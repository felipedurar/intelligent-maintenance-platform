import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  AlertTriangle, 
  MessageSquare, 
  ShieldCheck 
} from 'lucide-react';
import { healthService } from '../services/health';
import styles from './Layout.module.css';
import { clsx } from 'clsx';

const Layout: React.FC = () => {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => healthService.getHealth(),
    refetchInterval: 10000 // Check health every 10s
  });

  const isOnline = health?.status === 'ok';

  return (
    <div className={styles.container}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <ShieldCheck size={32} color="var(--brand-primary)" />
          <span>IMP v1.0</span>
        </div>
        
        <nav className={styles.nav}>
          <NavLink 
            to="/" 
            className={({ isActive }) => isActive ? styles.activeLink : styles.link}
          >
            <AlertTriangle size={20} />
            <span>Predictions</span>
          </NavLink>
          
          <NavLink 
            to="/assistant" 
            className={({ isActive }) => isActive ? styles.activeLink : styles.link}
          >
            <MessageSquare size={20} />
            <span>AI Assistant</span>
          </NavLink>
        </nav>
        
        <div className={styles.sidebarFooter}>
          <div className={clsx(styles.statusDot, isOnline ? styles.dotOnline : styles.dotOffline)} />
          <span>{isOnline ? 'System Online' : 'System Offline'}</span>
        </div>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <h1>Intelligent Maintenance Platform</h1>
          <div className={styles.userProfile}>
            <span>Technician: Admin</span>
          </div>
        </header>
        <section className={styles.content}>
          <Outlet />
        </section>
      </main>
    </div>
  );
};

export default Layout;
