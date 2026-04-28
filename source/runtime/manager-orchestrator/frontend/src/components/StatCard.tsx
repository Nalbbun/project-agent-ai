export default function StatCard({ title, value }: { title: string; value: number }) {
  return (
    <div className="card stat-card">
      <div className="card-label">{title}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
