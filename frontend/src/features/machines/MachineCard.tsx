import React from 'react';
import { Settings, Thermometer, RotateCcw, Activity, Clock } from 'lucide-react';
import type { Machine } from '../../types/machine';
import styles from './MachineCard.module.css';
import { clsx } from 'clsx';

interface MachineCardProps {
  machine: Machine;
  onClick?: (id: string) => void;
}

const MachineCard: React.FC<MachineCardProps> = ({ machine, onClick }) => {
  const statusClass = machine.status === 'critical' 
    ? styles.statusCritical 
    : machine.status === 'warning' 
    ? styles.statusWarning 
    : styles.statusNormal;

  return (
    <div className={styles.card} onClick={() => onClick?.(machine.id)}>
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <Settings size={20} className={styles.icon} />
          <div>
            <h3>{machine.name}</h3>
            <span className={styles.id}>{machine.id}</span>
          </div>
        </div>
        <div className={clsx(styles.statusBadge, statusClass)}>
          {machine.status.toUpperCase()}
        </div>
      </div>

      <div className={styles.stats}>
        <div className={styles.statItem}>
          <Thermometer size={16} />
          <span>{machine.telemetry.airTemperature.toFixed(1)}K</span>
        </div>
        <div className={styles.statItem}>
          <RotateCcw size={16} />
          <span>{machine.telemetry.rotationalSpeed} rpm</span>
        </div>
        <div className={styles.statItem}>
          <Activity size={16} />
          <span>{machine.telemetry.torque} Nm</span>
        </div>
      </div>

      <div className={styles.footer}>
        <Clock size={14} />
        <span>Última Manutenção: {machine.lastMaintenance}</span>
      </div>
    </div>
  );
};

export default MachineCard;
