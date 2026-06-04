import api from './api';
import type { Prediction, PredictionModel } from '@/types';

export async function listPredictions(): Promise<Prediction[]> {
  const { data } = await api.get<Prediction[]>('/predictions/');
  return data;
}

export async function listPredictionModels(): Promise<PredictionModel[]> {
  const { data } = await api.get<PredictionModel[]>('/prediction-models/');
  return data;
}

export async function generatePrediction(modelId: number): Promise<Prediction> {
  const { data } = await api.post<Prediction>('/predictions/generate/', { model_id: modelId });
  return data;
}
