export function firstLine(value) {
  return value.split("\n").find((line) => line.trim()) ?? "";
}

export function truncate(value, maxLength) {
  if (!value || value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 1)}...`;
}

export function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

export function formatTime(date) {
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}
