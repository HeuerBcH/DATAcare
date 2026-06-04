from rest_framework import serializers
from apps.users.models import User
from apps.patients.models import Patient, PatientVitals
from apps.predictions.models import PredictionModel, Prediction, PredictionFeedback


# ============= User Serializers =============
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone', 'cpf', 'profile_image', 'bio', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserDetailSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm', 'role']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': 'As senhas não coincidem.'})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# ============= Patient Serializers =============
class PatientVitalsSerializer(serializers.ModelSerializer):
    bmi = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientVitals
        fields = ['id', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'heart_rate', 'temperature', 'weight', 'height', 'blood_glucose', 'bmi', 'notes', 'measured_at']
        read_only_fields = ['id', 'measured_at']
    
    def get_bmi(self, obj):
        return obj.bmi


class PatientSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    age = serializers.SerializerMethodField()
    latest_vitals = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['id', 'user', 'cpf', 'date_of_birth', 'age', 'gender', 'blood_type', 'address', 'medical_history', 'allergies', 'emergency_contact', 'emergency_phone', 'latest_vitals', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_age(self, obj):
        return obj.age
    
    def get_latest_vitals(self, obj):
        vitals = obj.vitals.first()
        return PatientVitalsSerializer(vitals).data if vitals else None


class PatientDetailSerializer(PatientSerializer):
    vitals = serializers.SerializerMethodField()
    
    class Meta(PatientSerializer.Meta):
        fields = PatientSerializer.Meta.fields + ['vitals']
    
    def get_vitals(self, obj):
        vitals = obj.vitals.all()[:10]
        return PatientVitalsSerializer(vitals, many=True).data


class PatientCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['cpf', 'date_of_birth', 'gender', 'blood_type', 'address', 'medical_history', 'allergies', 'emergency_contact', 'emergency_phone']


class PatientVitalsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientVitals
        fields = ['blood_pressure_systolic', 'blood_pressure_diastolic', 'heart_rate', 'temperature', 'weight', 'height', 'blood_glucose', 'notes']


# ============= Prediction Serializers =============
class PredictionModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionModel
        fields = ['id', 'name', 'description', 'model_type', 'version', 'accuracy', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class PredictionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    model_name = serializers.CharField(source='model.name', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    
    class Meta:
        model = Prediction
        fields = ['id', 'patient', 'patient_name', 'model', 'model_name', 'risk_level', 'risk_level_display', 'probability', 'prediction_data', 'clinical_notes', 'recommended_actions', 'created_at']
        read_only_fields = ['id', 'patient', 'created_at']


class PredictionDetailSerializer(PredictionSerializer):
    feedback = serializers.SerializerMethodField()
    
    class Meta(PredictionSerializer.Meta):
        fields = PredictionSerializer.Meta.fields + ['feedback']
    
    def get_feedback(self, obj):
        if hasattr(obj, 'feedback'):
            return PredictionFeedbackSerializer(obj.feedback).data
        return None


class PredictionFeedbackSerializer(serializers.ModelSerializer):
    feedback_display = serializers.CharField(source='get_feedback_display', read_only=True)
    
    class Meta:
        model = PredictionFeedback
        fields = ['id', 'prediction', 'feedback', 'feedback_display', 'healthcare_professional', 'notes', 'created_at']
        read_only_fields = ['id', 'prediction', 'created_at']
