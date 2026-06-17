import { ReactNode } from 'react'
import clsx from 'clsx'

interface Props {
  title: string
  value: string | number
  subtitle?: string
  icon: ReactNode
  variant?: 'default' | 'danger' | 'warning' | 'success'
  trend?: { value: number; label: string }
}

const variantClasses = {
  default: 'bg-white border-slate-200',
  danger: 'bg-red-50 border-red-200',
  warning: 'bg-amber-50 border-amber-200',
  success: 'bg-emerald-50 border-emerald-200',
}

const iconBgClasses = {
  default: 'bg-teal-100 text-teal-700',
  danger: 'bg-red-100 text-red-700',
  warning: 'bg-amber-100 text-amber-700',
  success: 'bg-emerald-100 text-emerald-700',
}

export default function KPICard({
  title, value, subtitle, icon, variant = 'default', trend
}: Props) {
  return (
    <div className={clsx('rounded-xl border p-5 shadow-sm', variantClasses[variant])}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</p>
          <p className="mt-1 text-3xl font-bold text-slate-800">{value}</p>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          {trend && (
            <p className={clsx(
              'mt-2 text-xs font-medium',
              trend.value >= 0 ? 'text-red-600' : 'text-emerald-600'
            )}>
              {trend.value >= 0 ? '▲' : '▼'} {Math.abs(trend.value)}% {trend.label}
            </p>
          )}
        </div>
        <div className={clsx('rounded-lg p-2.5', iconBgClasses[variant])}>
          {icon}
        </div>
      </div>
    </div>
  )
}
