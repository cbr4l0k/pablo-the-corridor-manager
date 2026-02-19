export function getIsoWeekYearWeek(date: Date) {
  const utcDate = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const dayNum = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - dayNum);
  const isoYear = utcDate.getUTCFullYear();
  const yearStart = new Date(Date.UTC(isoYear, 0, 1));
  const weekNo = Math.ceil((((utcDate.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return { year: isoYear, weekNumber: weekNo };
}

export function getWeekStartAndDeadline(now: Date) {
  const day = now.getUTCDay() || 7;
  const monday = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  monday.setUTCDate(monday.getUTCDate() - (day - 1));
  monday.setUTCHours(0, 0, 0, 0);

  const deadline = new Date(monday.getTime());
  deadline.setUTCDate(deadline.getUTCDate() + 4);
  deadline.setUTCHours(12, 0, 0, 0);

  return { startDateMs: monday.getTime(), deadlineMs: deadline.getTime() };
}
