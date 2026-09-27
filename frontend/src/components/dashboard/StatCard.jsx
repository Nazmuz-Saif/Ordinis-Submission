function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5 flex items-center gap-4 hover:shadow-md transition-shadow duration-200">
      <div
        className="w-11 h-11 rounded-lg flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}1A`, color }}
      >
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-bold text-[#14142B]">{value}</p>
        <p className="text-sm text-[#71717A]">{label}</p>
      </div>
    </div>
  )
}

export default StatCard