import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Play, Activity, Thermometer, RotateCcw, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { predictionService } from '../../services/prediction';
import type { MachineObservation } from '../../types/api';
import styles from './PredictionsPage.module.css';
import { clsx } from 'clsx';

const PredictionsPage: React.FC = () => {
  const [formData, setFormData] = useState<MachineObservation>({
    product_type: 'L',
    air_temperature_k: 298.1,
    process_temperature_k: 308.6,
    rotational_speed_rpm: 1551,
    torque_nm: 42.8,
    tool_wear_min: 0
  });

  const mutation = useMutation({
    mutationFn: (data: MachineObservation) => predictionService.predictFailure({ observation: data }),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'product_type' ? value : parseFloat(value)
    }));
  };

  const result = mutation.data;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h2>Real-Time Failure Prediction</h2>
          <p>Enter sensor data to calculate the failure risk for the asset.</p>
        </div>
      </header>

      <div className={styles.layout}>
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Product Type</label>
              <select name="product_type" value={formData.product_type} onChange={handleChange}>
                <option value="L">Low (L)</option>
                <option value="M">Medium (M)</option>
                <option value="H">High (H)</option>
              </select>
            </div>

            <div className={styles.formGroup}>
              <label><Thermometer size={14} /> Air Temp. (K)</label>
              <input type="number" name="air_temperature_k" value={formData.air_temperature_k} onChange={handleChange} step="0.1" />
            </div>

            <div className={styles.formGroup}>
              <label><Thermometer size={14} /> Process Temp. (K)</label>
              <input type="number" name="process_temperature_k" value={formData.process_temperature_k} onChange={handleChange} step="0.1" />
            </div>

            <div className={styles.formGroup}>
              <label><RotateCcw size={14} /> Rotational Speed (RPM)</label>
              <input type="number" name="rotational_speed_rpm" value={formData.rotational_speed_rpm} onChange={handleChange} />
            </div>

            <div className={styles.formGroup}>
              <label><Activity size={14} /> Torque (Nm)</label>
              <input type="number" name="torque_nm" value={formData.torque_nm} onChange={handleChange} step="0.1" />
            </div>

            <div className={styles.formGroup}>
              <label>Tool Wear (min)</label>
              <input type="number" name="tool_wear_min" value={formData.tool_wear_min} onChange={handleChange} />
            </div>
          </div>

          <button type="submit" className={styles.submitButton} disabled={mutation.isPending}>
            {mutation.isPending ? 'Calculating...' : <><Play size={18} /> Run Prediction</>}
          </button>
        </form>

        <div className={styles.resultArea}>
          {mutation.isIdle && (
            <div className={styles.idleState}>
              <Activity size={48} />
              <p>Waiting for sensor parameters...</p>
            </div>
          )}

          {mutation.isSuccess && result && (
            <div className={clsx(
              styles.resultCard, 
              (result.failure_probability || 0) <= 0.5 ? styles.resultSuccess : styles.resultWarning
            )}>
              <div className={styles.resultHeader}>
                {(result.failure_probability || 0) <= 0.5 ? <CheckCircle2 size={32} /> : <AlertTriangle size={32} />}
                <div>
                  <h3>Analysis Result</h3>
                  <span className={styles.modelVersion}>Model: {result.model_version}</span>
                </div>
              </div>

              <div className={styles.probabilityGauge}>
                <span className={styles.probLabel}>Failure Probability</span>
                <span className={styles.probValue}>{((result.failure_probability || 0) * 100).toFixed(2)}%</span>
                <div className={styles.progressBar}>
                  <div 
                    className={styles.progressFill} 
                    style={{ width: `${(result.failure_probability || 0) * 100}%` }} 
                  />
                </div>
              </div>

              <div className={styles.riskClass}>
                <span>Risk Class:</span>
                <strong>{result.risk_class?.replace('_', ' ').toUpperCase()}</strong>
              </div>

              <p className={styles.resultMessage}>{result.message}</p>
            </div>
          )}

          {mutation.isError && (
            <div className={styles.errorCard}>
              <AlertTriangle size={32} />
              <p>Error processing prediction. Verify if the model is registered in MLflow.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PredictionsPage;
