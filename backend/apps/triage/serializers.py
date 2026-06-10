from datetime import date

from rest_framework import serializers

from .models import Alert, Comorbidity, Patient, Symptom, Visit, VisitSymptom


class SymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symptom
        fields = ["id", "name", "is_respiratory"]


class ComorbiditySerializer(serializers.ModelSerializer):
    class Meta:
        model = Comorbidity
        fields = ["id", "name", "is_critical"]


class PatientSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        fields = ["id", "full_name", "birth_date", "age", "gender", "phone", "address", "cpf", "created_at"]
        read_only_fields = ["id", "created_at"]


class VisitSymptomReadSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="symptom.name", read_only=True)
    is_respiratory = serializers.BooleanField(source="symptom.is_respiratory", read_only=True)

    class Meta:
        model = VisitSymptom
        fields = ["symptom", "name", "is_respiratory", "severity", "duration_days"]


class VisitSerializer(serializers.ModelSerializer):
    """Serializer de leitura de uma visita/triagem (com risco e sintomas)."""

    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    patient_age = serializers.IntegerField(source="patient.age", read_only=True)
    acs_name = serializers.CharField(source="acs.get_full_name", read_only=True, default=None)
    risk_level_display = serializers.CharField(source="get_risk_level_display", read_only=True)
    symptoms = VisitSymptomReadSerializer(source="visit_symptoms", many=True, read_only=True)
    comorbidities = ComorbiditySerializer(many=True, read_only=True)

    class Meta:
        model = Visit
        fields = [
            "id", "patient", "patient_name", "patient_age", "acs", "acs_name",
            "visit_date", "medications", "notes", "symptoms", "comorbidities",
            "risk_level", "risk_level_display", "risk_score", "model_version",
            "predicted_at", "created_at",
        ]
        read_only_fields = [
            "id", "risk_level", "risk_score", "model_version", "predicted_at", "created_at",
        ]


class _TriageSymptomInput(serializers.Serializer):
    name = serializers.CharField()
    severity = serializers.IntegerField(min_value=1, max_value=5, default=3)
    duration_days = serializers.IntegerField(min_value=0, default=1)


class TriageCreateSerializer(serializers.Serializer):
    """Recebe o formulário de triagem do ACS (HU-01) e cria paciente + visita,
    rodando a predição de risco e os alertas em seguida."""

    patient_id = serializers.IntegerField(required=False)
    patient = PatientSerializer(required=False)
    visit_date = serializers.DateField(required=False)
    medications = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    symptoms = _TriageSymptomInput(many=True, required=False, default=list)
    comorbidities = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    def validate(self, data):
        if not data.get("patient_id") and not data.get("patient"):
            raise serializers.ValidationError("Informe 'patient_id' ou os dados de 'patient'.")
        return data

    def create(self, validated):
        from src.ml.features import CRITICAL_COMORBIDITIES, RESPIRATORY_SYMPTOMS

        from .services import generate_alerts_for_visit, predict_and_store

        request = self.context.get("request")
        acs = request.user if request and request.user.is_authenticated else None

        if validated.get("patient_id"):
            try:
                patient = Patient.objects.get(pk=validated["patient_id"])
            except Patient.DoesNotExist:
                raise serializers.ValidationError({"patient_id": "Paciente não encontrado."})
        else:
            pdata = dict(validated["patient"])
            cpf = pdata.get("cpf")
            if cpf:
                patient, _ = Patient.objects.get_or_create(
                    cpf=cpf, defaults={**pdata, "registered_by": acs}
                )
            else:
                patient = Patient.objects.create(**pdata, registered_by=acs)

        visit = Visit.objects.create(
            patient=patient,
            acs=acs,
            visit_date=validated.get("visit_date") or date.today(),
            medications=validated.get("medications", ""),
            notes=validated.get("notes", ""),
        )

        for s in validated.get("symptoms", []):
            symptom, _ = Symptom.objects.get_or_create(
                name=s["name"], defaults={"is_respiratory": s["name"] in RESPIRATORY_SYMPTOMS}
            )
            VisitSymptom.objects.create(
                visit=visit,
                symptom=symptom,
                severity=s.get("severity", 3),
                duration_days=s.get("duration_days", 1),
            )

        com_objs = []
        for name in validated.get("comorbidities", []):
            comorbidity, _ = Comorbidity.objects.get_or_create(
                name=name, defaults={"is_critical": name in CRITICAL_COMORBIDITIES}
            )
            com_objs.append(comorbidity)
        if com_objs:
            visit.comorbidities.set(com_objs)

        predict_and_store(visit)
        generate_alerts_for_visit(visit)
        return visit


class AlertSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True, default=None)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    type_display = serializers.CharField(source="get_alert_type_display", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "alert_type", "type_display", "severity", "severity_display",
            "title", "message", "patient", "patient_name", "visit", "is_resolved", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
