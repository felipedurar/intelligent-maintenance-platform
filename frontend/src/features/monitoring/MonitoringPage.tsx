import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Activity, 
  ShieldAlert, 
  CheckCircle, 
  BarChart3, 
  Clock,
  AlertCircle
} from 'lucide-react';
import { monitoringService } from './monitoringService';
import styles from './MonitoringPage.module.css';
import { clsx } from 'clsx';

const MonitoringPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['monitoring-status'],
    queryFn: () => monitoringService.getStatus(),
    refetchInterval: 30000 // Auto-refresh every 30s
  });

  if (isLoading) return <div>Carregando métricas de monitoramento...</div>;
  if (error) return <div>Erro ao carregar monitoramento. Verifique a API.</div>;

  const hasDrift = data?.drift?.drifted_features && data.drift.drifted_features.length > 0;
  const hasWarning = data?.drift?.warning_features && data.drift.warning_features.length > 0;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h2>Monitoramento de ML & Saúde</h2>
          <p>Estado dos modelos de IA, detecção de drift e métricas operacionais.</p>
        </div>
        <div className={clsx(
          styles.statusBadge, 
          data?.status === 'stable' ? styles.statusStable : styles.statusIssues
        )}>
          {data?.status.toUpperCase() || 'UNKNOWN'}
        </div>
      </header>

      <div className={styles.grid}>
        {/* ML Drift Section */}
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <ShieldAlert size={20} className={styles.icon} />
            <h3>Detecção de Drift (PSI)</h3>
          </div>
          
          {data?.drift?.generated_at ? (
            <div className={styles.cardContent}>
              <div className={styles.psiMetric}>
                <span className={styles.label}>Max Feature PSI</span>
                <span className={clsx(
                  styles.value, 
                  (data.drift.max_feature_psi || 0) > 0.2 ? styles.textCritical : 
                  (data.drift.max_feature_psi || 0) > 0.1 ? styles.textWarning : styles.textNormal
                )}>
                  {data.drift.max_feature_psi?.toFixed(4) || '0.0000'}
                </span>
              </div>
              
              <div className={styles.driftList}>
                <div className={styles.driftCategory}>
                  <span className={styles.categoryTitle}>Features com Drift (PSI &gt; 0.2)</span>
                  {hasDrift ? (
                    <ul>
                      {data.drift.drifted_features.map(f => <li key={f} className={styles.criticalItem}>{f}</li>)}
                    </ul>
                  ) : <p className={styles.emptyText}>Nenhuma feature detectada.</p>}
                </div>

                <div className={styles.driftCategory}>
                  <span className={styles.categoryTitle}>Alertas (PSI &gt; 0.1)</span>
                  {hasWarning ? (
                    <ul>
                      {data.drift.warning_features.map(f => <li key={f} className={styles.warningItem}>{f}</li>)}
                    </ul>
                  ) : <p className={styles.emptyText}>Nenhum alerta pendente.</p>}
                </div>
              </div>
              
              <div className={styles.cardFooter}>
                <Clock size={14} />
                <span>Gerado em: {data.drift.generated_at}</span>
              </div>
            </div>
          ) : (
            <div className={styles.emptyState}>
              <AlertCircle size={32} />
              <p>Nenhum relatório de drift encontrado. Execute o fluxo de monitoramento no Prefect.</p>
            </div>
          )}
        </section>

        {/* Operational Metrics */}
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <Activity size={20} className={styles.icon} />
            <h3>Métricas Observáveis (Prometheus)</h3>
          </div>
          <div className={styles.cardContent}>
            <p className={styles.description}>
              Os seguintes contadores e histogramas estão sendo exportados para o Prometheus:
            </p>
            <div className={styles.metricsGrid}>
              {data?.metrics.map(metric => (
                <div key={metric} className={styles.metricItem}>
                  <BarChart3 size={14} />
                  <span>{metric}</span>
                </div>
              ))}
            </div>
            <div className={styles.infoBox}>
              <CheckCircle size={16} />
              <span>Integração com Grafana: Ativa</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default MonitoringPage;
