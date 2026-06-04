import api from './api';
import type { Patient } from '@/types';

export async function listPatients(): Promise<Patient[]> {
  const { data } = await api.get<Patient[]>('/patients/');
  return data;
}

export async function getMyPatient(): Promise<Patient> {
  const { data } = await api.get<Patient>('/patients/me/');
  return data;
}
