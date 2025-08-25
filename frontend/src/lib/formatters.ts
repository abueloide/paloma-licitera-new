export const formatMoney = (amount: number): string => {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat('es-MX').format(num);
};

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

export const getBadgeColor = (fuente: string): string => {
  switch (fuente.toLowerCase()) {
    case 'tianguis':
      return 'badge-tianguis';
    case 'comprasmx':
      return 'badge-comprasmx';
    case 'dof':
      return 'badge-dof';
    default:
      return 'badge-tianguis';
  }
};

export const getEstadoBadgeColor = (estado: string): string => {
  switch (estado.toLowerCase()) {
    case 'vigente':
      return 'bg-green-100 text-green-800';
    case 'cerrado':
      return 'bg-red-100 text-red-800';
    case 'suspendido':
      return 'bg-yellow-100 text-yellow-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};