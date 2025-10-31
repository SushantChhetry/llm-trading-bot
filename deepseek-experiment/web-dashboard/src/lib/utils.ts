import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number | null | undefined): string {
  // Handle null, undefined, NaN, and invalid numbers
  if (value === null || value === undefined || isNaN(value) || !isFinite(value)) {
    return '$0.00'
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatPercentage(value: number | null | undefined): string {
  // Handle null, undefined, NaN, and invalid numbers
  if (value === null || value === undefined || isNaN(value) || !isFinite(value)) {
    return '0.00%'
  }
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value / 100)
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value)
}

export function getProfitColor(profit: number): string {
  if (profit > 0) return 'profit-positive'
  if (profit < 0) return 'profit-negative'
  return 'profit-neutral'
}

export function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString('en-US', {
    timeZone: 'America/New_York', // EST/EDT
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatTimestampFull(timestamp: string): string {
  return new Date(timestamp).toLocaleString('en-US', {
    timeZone: 'America/New_York', // EST/EDT
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatTimeOnly(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString('en-US', {
    timeZone: 'America/New_York', // EST/EDT
    hour: '2-digit',
    minute: '2-digit',
  })
}
