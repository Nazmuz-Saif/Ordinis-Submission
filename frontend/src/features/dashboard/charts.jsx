import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

// Violet palette from the design system. Charts always use these.
const VIOLET = '#6C31D6'
const PALETTE = ['#6C31D6', '#A78BFA', '#4C1D95', '#C4B5FD', '#7C3AED', '#DDD6FE']

// initialDimension lets the chart draw before the browser has measured the box.
const INITIAL = { width: 480, height: 240 }

// Vertical bars: [{ name, value }]. colors (optional) = one colour per bar.
export function BarChartBox({ data, colors, height = 240, valueLabel = 'Count', formatValue }) {
  return (
    <div data-testid="bar-chart" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%" initialDimension={INITIAL}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEEEF2" />
          <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#71717A' }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#71717A' }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ fill: '#EDE9FE' }}
            formatter={(v) => [formatValue ? formatValue(v) : v, valueLabel]}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]} fill={VIOLET} isAnimationActive={false}>
            {colors && data.map((d, i) => <Cell key={d.name} fill={colors[i % colors.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// Donut: [{ name, value }] with a small legend underneath.
export function DonutChartBox({ data, height = 240 }) {
  return (
    <div data-testid="donut-chart">
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%" initialDimension={INITIAL}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="85%" paddingAngle={2} isAnimationActive={false}>
              {data.map((d, i) => <Cell key={d.name} fill={PALETTE[i % PALETTE.length]} />)}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-[#71717A]">
        {data.map((d, i) => (
          <li key={d.name} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
            {d.name} ({d.value})
          </li>
        ))}
      </ul>
    </div>
  )
}

// Line over time: [{ short, label, rate }]. rate is a percentage from 0 to 100.
export function LineChartBox({ data, height = 260, valueLabel = 'Rate' }) {
  return (
    <div data-testid="line-chart" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%" initialDimension={INITIAL}>
        <LineChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEEEF2" />
          <XAxis dataKey="short" tick={{ fontSize: 12, fill: '#71717A' }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12, fill: '#71717A' }} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(v) => [`${v}%`, valueLabel]}
            labelFormatter={(_label, payload) => (payload && payload[0] ? payload[0].payload.label : _label)}
          />
          <Line type="monotone" dataKey="rate" stroke={VIOLET} strokeWidth={2.5} dot={{ r: 4, fill: VIOLET }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// Two bars side by side per name: [{ name, completed, pending }]. Dark violet = completed, light violet = pending.
export function GroupedBarChartBox({ data, height = 260 }) {
  return (
    <div data-testid="grouped-bar-chart" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%" initialDimension={INITIAL}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEEEF2" />
          <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#71717A' }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#71717A' }} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: '#EDE9FE' }} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="completed" name="Completed" fill={VIOLET} radius={[6, 6, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="pending" name="Pending" fill="#C4B5FD" radius={[6, 6, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
