import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Database, Table, CheckCircle2, AlertCircle } from 'lucide-react';
import { machineService } from './machineService';
import styles from './MachinesPage.module.css';
import { clsx } from 'clsx';

const MachinesPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dataset-status'],
    queryFn: () => machineService.getDatasetStatus(),
  });

  if (isLoading) return <div>Carregando status do dataset...</div>;
  if (error) return <div>Erro ao carregar dados do inventário.</div>;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h2>Inventário de Dados (AI4I 2020)</h2>
          <p>Status de ingestão e esquema de dados para manutenção preditiva.</p>
        </div>
      </header>

      <div className={styles.statusCard}>
        <div className={styles.statusHeader}>
          <Database size={24} className={styles.icon} />
          <h3>Status da Ingestão</h3>
        </div>
        <div className={styles.statusContent}>
          <div className={styles.statusRow}>
            <span className={styles.label}>Dataset:</span>
            <span className={styles.value}>{data?.dataset}</span>
          </div>
          <div className={styles.statusRow}>
            <span className={styles.label}>Status:</span>
            <div className={clsx(
              styles.badge, 
              data?.status === 'ingested' ? styles.badgeSuccess : styles.badgeWarning
            )}>
              {data?.status === 'ingested' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
              {data?.status.toUpperCase()}
            </div>
          </div>
          <p className={styles.message}>{data?.message}</p>
        </div>
      </div>

      <div className={styles.schemaSection}>
        <div className={styles.sectionHeader}>
          <Table size={20} />
          <h3>Esquema de Dados Esperado</h3>
        </div>
        <div className={styles.columnsGrid}>
          {data?.expected_columns.map(col => (
            <div key={col} className={styles.columnItem}>
              {col}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MachinesPage;
