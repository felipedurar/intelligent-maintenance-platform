import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Activity, 
  CheckCircle, 
  Server,
  Zap,
  ShieldCheck
} from 'lucide-react';
import { healthService } from '../../services/health';
import { monitoringService } from '../monitoring/monitoringService';
import styles from './Dashboard.module.css';

const Dashboard: React.FC = () => {
  const { data: health } = useQuery({
    queryKey: ['health-summary'],
    queryFn: () => healthService.getHealth(),
  });

  const { data: monitor } = useQuery({
    queryKey: ['monitoring-summary'],
    queryFn: () => monitoringService.getStatus(),
  });

  const isOnline = health?.status === 'ok';

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h2>Visão Geral da Plataforma</h2>
        <span className={styles.date}>{new Date().toLocaleDateString('pt-BR')}</span>
      </header>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ color: isOnline ? 'var(--status-normal)' : 'var(--status-critical)' }}>
            <Server size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statLabel}>Status API</span>
            <span className={styles.statValue}>{isOnline ? 'ONLINE' : 'OFFLINE'}</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ color: 'var(--brand-primary)' }}>
            <Zap size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statLabel}>Versão App</span>
            <span className={styles.statValue}>{health?.version || '---'}</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ color: 'var(--status-warning)' }}>
            <Activity size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statLabel}>Max PSI (Drift)</span>
            <span className={styles.statValue}>{monitor?.drift?.max_feature_psi?.toFixed(4) || '0.0000'}</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ color: 'var(--brand-secondary)' }}>
            <ShieldCheck size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statLabel}>Ambiente</span>
            <span className={styles.statValue}>{health?.environment?.toUpperCase() || '---'}</span>
          </div>
        </div>
      </div>

      <div className={styles.mainGrid}>
        <div className={styles.infoArea}>
          <h3>Métricas Operacionais</h3>
          <div className={styles.metricsList}>
            {monitor?.metrics.slice(0, 6).map(metric => (
              <div key={metric} className={styles.metricItem}>
                <CheckCircle size={14} color="var(--status-normal)" />
                <span>{metric}</span>
              </div>
            ))}
          </div>
        </div>
        
        <div className={styles.alertsArea}>
          <h3>Alertas do Sistema</h3>
          <div className={styles.eventList}>
            {monitor?.drift?.drifted_features.length ? (
              monitor.drift.drifted_features.map(f => (
                <div key={f} className={styles.eventItem}>
                  <div className={styles.eventDot} style={{ backgroundColor: 'var(--status-critical)' }} />
                  <div>
                    <p><strong>Drift Crítico Detectado:</strong> {f}</p>
                    <span>PSI &gt; 0.2</span>
                  </div>
                </div>
              ))
            ) : (
              <div className={styles.eventItem}>
                <div className={styles.eventDot} style={{ backgroundColor: 'var(--status-normal)' }} />
                <div>
                  <p>Nenhum desvio detectado no modelo.</p>
                  <span>Sensores operando dentro da normalidade.</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
