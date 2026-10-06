
import { useEffect, useMemo, useState } from 'react'
import {
    DollarSign,
    Plus,
    Search,
    MoreHorizontal,
    Pencil,
    Trash2,
    Eye,
    X,
    Download,
    CalendarDays,
    ChevronDown,
    SlidersHorizontal,
    LayoutGrid,
    List,
    Sparkles,
    Clock3,
    Gift,
    Wallet,
} from 'lucide-react'
import {
    getSalaryStructures,
    createSalaryStructure,
    updateSalaryStructure,
    deleteSalaryStructure,
} from '../../services/payrollService'
import { getEmployees } from '../../services/organizationService'
import { useAuth } from '../../store/AuthContext'

function SalaryStructuresPage() {
    const [salaryStructures, setSalaryStructures] = useState([])
    const [employees, setEmployees] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [search, setSearch] = useState('')
    const [showModal, setShowModal] = useState(false)
    const [editingId, setEditingId] = useState(null)
    const [viewingStructure, setViewingStructure] = useState(null)
    const [openMenuId, setOpenMenuId] = useState(null)
    const [viewMode, setViewMode] = useState('list')
    const [chartMode, setChartMode] = useState('Month')

    const [form, setForm] = useState({
        employee: '',
        base_salary: '',
        house_rent: '',
        medical: '',
        transport: '',
        other: '',
        effective_from: '',
    })

    const { hasPermission } = useAuth()
    const canManageSalary = hasPermission('finance')

    async function loadAll() {
        setLoading(true)
        setError('')

        try {
            const [structures, emps] = await Promise.all([
                getSalaryStructures(),
                getEmployees(),
            ])

            setSalaryStructures(structures)
            setEmployees(emps)
        } catch (err) {
            setError(
                err.response?.data?.error?.message ||
                'Failed to load salary structures.'
            )
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (canManageSalary) {
            loadAll()
        } else {
            setLoading(false)
        }
    }, [canManageSalary])

    function handleChange(e) {
        setForm({
            ...form,
            [e.target.name]: e.target.value,
        })
    }

    function resetForm() {
        setForm({
            employee: '',
            base_salary: '',
            house_rent: '',
            medical: '',
            transport: '',
            other: '',
            effective_from: '',
        })

        setEditingId(null)
        setShowModal(false)
    }

    function openCreateModal() {
        setError('')
        setEditingId(null)

        setForm({
            employee: '',
            base_salary: '',
            house_rent: '',
            medical: '',
            transport: '',
            other: '',
            effective_from: '',
        })

        setShowModal(true)
    }

    function openEditModal(structure) {
        const allowances = structure.allowances || {}

        setError('')
        setEditingId(structure.id)

        setForm({
            employee: structure.employee || '',
            base_salary: structure.base_salary || '',
            house_rent: allowances.house_rent || '',
            medical: allowances.medical || '',
            transport: allowances.transport || '',
            other: allowances.other || '',
            effective_from: structure.effective_from || '',
        })

        setOpenMenuId(null)
        setShowModal(true)
    }

    async function handleSubmit(e) {
        e.preventDefault()
        setError('')

        const payload = {
            employee: form.employee,
            base_salary: form.base_salary,
            allowances: {
                house_rent: form.house_rent || 0,
                medical: form.medical || 0,
                transport: form.transport || 0,
                other: form.other || 0,
            },
            effective_from: form.effective_from,
        }

        try {
            if (editingId) {
                await updateSalaryStructure(editingId, payload)
            } else {
                await createSalaryStructure(payload)
            }

            resetForm()
            await loadAll()
        } catch (err) {
            setError(
                err.response?.data?.error?.message ||
                `Failed to ${editingId ? 'update' : 'create'} salary structure.`
            )
        }
    }

    async function handleDelete(id) {
        const confirmed = window.confirm(
            'Are you sure you want to delete this salary structure?'
        )

        if (!confirmed) {
            return
        }

        setError('')
        setOpenMenuId(null)

        try {
            await deleteSalaryStructure(id)
            await loadAll()
        } catch (err) {
            setError(
                err.response?.data?.error?.message ||
                'Failed to delete salary structure.'
            )
        }
    }

    function getTotalAllowances(structure) {
        const allowances = structure.allowances || {}

        return (
            Number(allowances.house_rent || 0) +
            Number(allowances.medical || 0) +
            Number(allowances.transport || 0) +
            Number(allowances.other || 0)
        )
    }

    function getGrossSalary(structure) {
        return Number(structure.base_salary || 0) + getTotalAllowances(structure)
    }

    function formatCurrency(value) {
        return `$${Number(value || 0).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        })
            } `
    }

    function getEmployeeInfo(structure) {
        const employee = employees.find(
            (item) => String(item.id) === String(structure.employee)
        )

        return employee
    }

    function getEmployeePosition(structure) {
        const employee = getEmployeeInfo(structure)

        return (
            employee?.designation_name ||
            employee?.designation?.name ||
            employee?.designation ||
            'Employee'
        )
    }

    const filteredStructures = useMemo(() => {
        const query = search.trim().toLowerCase()

        if (!query) {
            return salaryStructures
        }

        return salaryStructures.filter((structure) => {
            return (
                structure.employee_name?.toLowerCase().includes(query) ||
                structure.employee_code?.toLowerCase().includes(query) ||
                getEmployeePosition(structure).toLowerCase().includes(query) ||
                String(structure.base_salary || '').includes(query)
            )
        })
    }, [salaryStructures, search, employees])

    const totalPayroll = salaryStructures.reduce(
        (total, structure) => total + getGrossSalary(structure),
        0
    )

    const averageSalary =
        salaryStructures.length > 0
            ? totalPayroll / salaryStructures.length
            : 0

    const chartValues = useMemo(() => {
        if (salaryStructures.length === 0) {
            return [
                { label: 'Jan', payroll: 0, overtime: 0, bonus: 0 },
                { label: 'Feb', payroll: 0, overtime: 0, bonus: 0 },
                { label: 'Mar', payroll: 0, overtime: 0, bonus: 0 },
                { label: 'Apr', payroll: 0, overtime: 0, bonus: 0 },
                { label: 'May', payroll: 0, overtime: 0, bonus: 0 },
                { label: 'Jun', payroll: 0, overtime: 0, bonus: 0 },
                { label: 'Jul', payroll: 0, overtime: 0, bonus: 0 },
                { label: 'Aug', payroll: 0, overtime: 0, bonus: 0 },
                { label: 'Sep', payroll: 0, overtime: 0, bonus: 0 },
            ]
        }

        const labels = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
        ]

        return labels.map((label, index) => {
            const factor = 0.72 + (index % 4) * 0.07

            return {
                label,
                payroll: totalPayroll * factor,
                overtime: totalPayroll * 0.07 * factor,
                bonus: totalPayroll * 0.04 * (0.8 + (index % 3) * 0.1),
            }
        })
    }, [totalPayroll])

    const chartMax = Math.max(
        ...chartValues.map((item) => item.payroll),
        1
    )

    function exportCSV() {
        const rows = [
            [
                'Employee',
                'Position',
                'Salary',
                'Recurring',
                'Overtime',
                'Status',
            ],
            ...filteredStructures.map((structure) => [
                structure.employee_name || '',
                getEmployeePosition(structure),
                getGrossSalary(structure),
                'Recurring',
                '-',
                'Paid',
            ]),
        ]

        const csv = rows
            .map((row) =>
                row
                    .map((value) =>
                        `"${String(value).replaceAll('"', '""')}"`
                    )
                    .join(',')
            )
            .join('\n')

        const blob = new Blob([csv], {
            type: 'text/csv;charset=utf-8;',
        })

        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')

        link.href = url
        link.download = 'payroll.csv'
        link.click()

        URL.revokeObjectURL(url)
    }

    if (!canManageSalary) {
        return (
            <div className="min-h-full">
                <div className="bg-white rounded-2xl border border-[#EEEEF2] p-8">
                    <h1 className="text-2xl font-bold text-[#14142B]">
                        Payroll
                    </h1>

                    <p className="text-sm text-[#71717A] mt-2">
                        You do not have permission to view payroll information.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-full bg-[#F8F8FA] -m-6 p-6">
            {/* Payroll Header */}
            <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4 mb-7">
                <div>
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold text-[#14142B]">
                            Payroll
                        </h1>

                        <span className="text-[#D4D4D8]">/</span>

                        <span className="text-sm text-[#71717A]">
                            Payroll Settings
                        </span>
                    </div>

                    <p className="text-sm text-[#A1A1AA] mt-1">
                        Manage employee salaries, allowances and payroll.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <button
                        type="button"
                        className="inline-flex items-center gap-2 bg-white border border-[#E4E4E7] rounded-lg px-3.5 py-2.5 text-sm text-[#3F3F46]"
                    >
                        <CalendarDays size={16} />
                        26 Jan 2024 — 25 Feb 2024
                        <ChevronDown size={15} />
                    </button>

                    <button
                        type="button"
                        onClick={exportCSV}
                        className="inline-flex items-center gap-2 bg-[#14142B] text-white rounded-lg px-4 py-2.5 text-sm font-medium hover:opacity-90"
                    >
                        <Download size={16} />
                        Export CSV
                    </button>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 rounded-xl p-3 mb-6 text-sm">
                    {error}
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white border border-[#EEEEF2] rounded-2xl p-5">
                    <div className="flex items-start justify-between">
                        <div>
                            <p className="text-sm text-[#71717A]">
                                Monthly Payroll
                            </p>

                            <p className="text-2xl font-bold text-[#14142B] mt-2">
                                {formatCurrency(totalPayroll)}
                            </p>

                            <div className="flex items-center gap-2 mt-2">
                                <span className="text-xs font-medium text-red-500">
                                    -12.5%
                                </span>

                                <span className="text-xs text-[#A1A1AA]">
                                    vs previous month
                                </span>
                            </div>
                        </div>

                        <div className="w-10 h-10 rounded-xl bg-[#F4F4F5] flex items-center justify-center">
                            <Wallet
                                size={19}
                                className="text-[#3F3F46]"
                            />
                        </div>
                    </div>
                </div>

                <div className="bg-white border border-[#EEEEF2] rounded-2xl p-5">
                    <div className="flex items-start justify-between">
                        <div>
                            <p className="text-sm text-[#71717A]">
                                Overtime
                            </p>

                            <p className="text-2xl font-bold text-[#14142B] mt-2">
                                {formatCurrency(0)}
                            </p>

                            <div className="flex items-center gap-2 mt-2">
                                <span className="text-xs font-medium text-red-500">
                                    -5.3%
                                </span>

                                <span className="text-xs text-[#A1A1AA]">
                                    vs previous month
                                </span>
                            </div>
                        </div>

                        <div className="w-10 h-10 rounded-xl bg-[#F4F4F5] flex items-center justify-center">
                            <Clock3
                                size={19}
                                className="text-[#3F3F46]"
                            />
                        </div>
                    </div>
                </div>

                <div className="bg-white border border-[#EEEEF2] rounded-2xl p-5">
                    <div className="flex items-start justify-between">
                        <div>
                            <p className="text-sm text-[#71717A]">
                                Bonuses & Incentives
                            </p>

                            <p className="text-2xl font-bold text-[#14142B] mt-2">
                                {formatCurrency(0)}
                            </p>

                            <div className="flex items-center gap-2 mt-2">
                                <span className="text-xs font-medium text-green-600">
                                    +12.3%
                                </span>

                                <span className="text-xs text-[#A1A1AA]">
                                    vs previous month
                                </span>
                            </div>
                        </div>

                        <div className="w-10 h-10 rounded-xl bg-[#F4F4F5] flex items-center justify-center">
                            <Gift
                                size={19}
                                className="text-[#3F3F46]"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Overview */}
            <div className="bg-white border border-[#EEEEF2] rounded-2xl p-5 mb-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
                    <div>
                        <h2 className="text-base font-semibold text-[#14142B]">
                            Overview
                        </h2>

                        <p className="text-xs text-[#A1A1AA] mt-1">
                            Payroll activity over time
                        </p>
                    </div>

                    <div className="flex items-center bg-[#F4F4F5] rounded-lg p-1">
                        {['Day', 'Week', 'Month'].map((item) => (
                            <button
                                key={item}
                                type="button"
                                onClick={() => setChartMode(item)}
                                className={`px-3 py-1.5 rounded-md text-xs font-medium ${chartMode === item
                                    ? 'bg-white text-[#14142B] shadow-sm'
                                    : 'text-[#71717A]'
                                    }`}
                            >
                                {item}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex gap-5">
                    <div className="flex flex-col justify-between h-64 text-[10px] text-[#A1A1AA] py-1">
                        <span>$400k</span>
                        <span>$300k</span>
                        <span>$200k</span>
                        <span>$100k</span>
                        <span>$0</span>
                    </div>

                    <div className="flex-1">
                        <div className="h-64 flex items-end gap-3 border-b border-[#EEEEF2]">
                            {chartValues.map((item) => {
                                const height =
                                    item.payroll > 0
                                        ? Math.max(
                                            (item.payroll / chartMax) * 88,
                                            8
                                        )
                                        : 3

                                return (
                                    <div
                                        key={item.label}
                                        className="flex-1 h-full flex items-end justify-center"
                                    >
                                        <div
                                            className="w-full max-w-10 rounded-t-md bg-[#27272A]"
                                            style={{
                                                height: `${height}%`,
                                            }}
                                            title={`${item.label}: ${formatCurrency(
                                                item.payroll
                                            )}`}
                                        />
                                    </div>
                                )
                            })}
                        </div>

                        <div className="flex gap-3 pt-3">
                            {chartValues.map((item) => (
                                <span
                                    key={item.label}
                                    className="flex-1 text-center text-[10px] text-[#A1A1AA]"
                                >
                                    {item.label}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-5 mt-5 text-xs text-[#71717A]">
                    <span className="inline-flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-[#27272A]" />
                        Monthly Payroll
                    </span>

                    <span className="inline-flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-[#A1A1AA]" />
                        Overtime
                    </span>

                    <span className="inline-flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-[#D4D4D8]" />
                        Bonuses & Incentives
                    </span>
                </div>
            </div>

            {/* AI Card */}
            <div className="bg-[#18181B] text-white rounded-2xl p-6 mb-7">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5">
                    <div className="flex items-start gap-4">
                        <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center shrink-0">
                            <Sparkles size={20} />
                        </div>

                        <div>
                            <p className="text-sm font-semibold">
                                Stella AI
                            </p>

                            <p className="text-lg font-semibold mt-1">
                                Generate your financial report with ease
                            </p>

                            <p className="text-sm text-white/60 mt-1">
                                Get useful insights from your payroll data with
                                your AI personal assistant.
                            </p>
                        </div>
                    </div>

                    <button
                        type="button"
                        className="shrink-0 bg-white text-[#18181B] rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-white/90"
                    >
                        Try now!
                    </button>
                </div>
            </div>

            {/* Employee Header */}
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-4">
                <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold text-[#14142B]">
                        Employee
                    </h2>

                    <span className="text-xs text-[#A1A1AA]">
                        {filteredStructures.length} employees
                    </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <button
                        type="button"
                        onClick={openCreateModal}
                        className="inline-flex items-center gap-2 bg-[#14142B] text-white rounded-lg px-3.5 py-2.5 text-sm font-medium"
                    >
                        <Plus size={16} />
                        Add Structure
                    </button>

                    <button
                        type="button"
                        className="inline-flex items-center gap-2 bg-white border border-[#E4E4E7] rounded-lg px-3.5 py-2.5 text-sm text-[#3F3F46]"
                    >
                        <SlidersHorizontal size={16} />
                        Filter
                    </button>

                    <div className="relative">
                        <Search
                            size={16}
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1AA]"
                        />

                        <input
                            type="text"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search employee"
                            className="w-48 sm:w-60 bg-white border border-[#E4E4E7] rounded-lg pl-9 pr-3 py-2.5 text-sm outline-none focus:border-[#14142B]"
                        />
                    </div>

                    <div className="flex items-center bg-white border border-[#E4E4E7] rounded-lg p-1">
                        <button
                            type="button"
                            onClick={() => setViewMode('grid')}
                            className={`w-8 h-8 flex items-center justify-center rounded-md ${viewMode === 'grid'
                                ? 'bg-[#F4F4F5] text-[#14142B]'
                                : 'text-[#A1A1AA]'
                                }`}
                        >
                            <LayoutGrid size={16} />
                        </button>

                        <button
                            type="button"
                            onClick={() => setViewMode('list')}
                            className={`w-8 h-8 flex items-center justify-center rounded-md ${viewMode === 'list'
                                ? 'bg-[#F4F4F5] text-[#14142B]'
                                : 'text-[#A1A1AA]'
                                }`}
                        >
                            <List size={16} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Employee List / Grid */}
            {loading ? (
                <div className="bg-white border border-[#EEEEF2] rounded-2xl p-10 text-center text-sm text-[#71717A]">
                    Loading payroll...
                </div>
            ) : filteredStructures.length === 0 ? (
                <div className="bg-white border border-[#EEEEF2] rounded-2xl p-12 text-center">
                    <DollarSign
                        size={34}
                        className="mx-auto text-[#A1A1AA] mb-3"
                    />

                    <h3 className="font-medium text-[#14142B]">
                        No employees found
                    </h3>

                    <p className="text-sm text-[#71717A] mt-1">
                        {search
                            ? 'Try a different search term.'
                            : 'Create your first salary structure to get started.'}
                    </p>

                    {!search && (
                        <button
                            type="button"
                            onClick={openCreateModal}
                            className="mt-4 inline-flex items-center gap-2 bg-[#14142B] text-white rounded-lg px-4 py-2.5 text-sm font-medium"
                        >
                            <Plus size={16} />
                            Add Structure
                        </button>
                    )}
                </div>
            ) : viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {filteredStructures.map((structure) => (
                        <div
                            key={structure.id}
                            className="bg-white border border-[#EEEEF2] rounded-2xl p-5"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-[#F4F4F5] flex items-center justify-center font-semibold text-[#3F3F46]">
                                        {(
                                            structure.employee_name || 'E'
                                        )
                                            .charAt(0)
                                            .toUpperCase()}
                                    </div>

                                    <div>
                                        <p className="font-medium text-[#14142B]">
                                            {structure.employee_name}
                                        </p>

                                        <p className="text-xs text-[#A1A1AA] mt-0.5">
                                            {structure.employee_code}
                                        </p>
                                    </div>
                                </div>

                                <button
                                    type="button"
                                    onClick={() =>
                                        setOpenMenuId(
                                            openMenuId === structure.id
                                                ? null
                                                : structure.id
                                        )
                                    }
                                    className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-[#F4F4F5]"
                                >
                                    <MoreHorizontal
                                        size={18}
                                        className="text-[#71717A]"
                                    />
                                </button>
                            </div>

                            <div className="mt-5">
                                <p className="text-xs text-[#A1A1AA]">
                                    Position
                                </p>

                                <p className="text-sm font-medium text-[#3F3F46] mt-1">
                                    {getEmployeePosition(structure)}
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mt-5">
                                <div>
                                    <p className="text-xs text-[#A1A1AA]">
                                        Salary
                                    </p>

                                    <p className="text-sm font-semibold text-[#14142B] mt-1">
                                        {formatCurrency(
                                            getGrossSalary(structure)
                                        )}
                                    </p>
                                </div>

                                <div>
                                    <p className="text-xs text-[#A1A1AA]">
                                        Recurring
                                    </p>

                                    <p className="text-sm font-medium text-[#3F3F46] mt-1">
                                        Recurring
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-center justify-between mt-5 pt-4 border-t border-[#F4F4F5]">
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 text-green-700 px-2.5 py-1 text-xs font-medium">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                                    Paid
                                </span>

                                <button
                                    type="button"
                                    onClick={() =>
                                        setViewingStructure(structure)
                                    }
                                    className="text-xs font-medium text-[#3F3F46] hover:underline"
                                >
                                    View details
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="bg-white border border-[#EEEEF2] rounded-2xl overflow-visible">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left border-b border-[#EEEEF2] bg-[#FAFAFA]">
                                    <th className="p-4 w-10">
                                        <input
                                            type="checkbox"
                                            className="rounded border-[#D4D4D8]"
                                        />
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Employee
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Position
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Salary
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Recurring
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Overtime
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Status
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A] text-right">
                                        Actions
                                    </th>
                                </tr>
                            </thead>

                            <tbody>
                                {filteredStructures.map((structure) => (
                                    <tr
                                        key={structure.id}
                                        className="border-b border-[#F4F4F5] last:border-b-0 hover:bg-[#FAFAFA]"
                                    >
                                        <td className="p-4">
                                            <input
                                                type="checkbox"
                                                className="rounded border-[#D4D4D8]"
                                            />
                                        </td>

                                        <td className="p-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-9 h-9 rounded-full bg-[#F4F4F5] flex items-center justify-center font-semibold text-xs text-[#3F3F46] shrink-0">
                                                    {(
                                                        structure.employee_name ||
                                                        'E'
                                                    )
                                                        .charAt(0)
                                                        .toUpperCase()}
                                                </div>

                                                <div>
                                                    <div className="font-medium text-[#14142B]">
                                                        {
                                                            structure.employee_name
                                                        }
                                                    </div>

                                                    <div className="text-xs text-[#A1A1AA] mt-0.5">
                                                        {
                                                            structure.employee_code
                                                        }
                                                    </div>
                                                </div>
                                            </div>
                                        </td>

                                        <td className="p-4 text-[#3F3F46]">
                                            {getEmployeePosition(structure)}
                                        </td>

                                        <td className="p-4 font-medium text-[#14142B]">
                                            {formatCurrency(
                                                getGrossSalary(structure)
                                            )}
                                        </td>

                                        <td className="p-4 text-[#71717A]">
                                            Recurring
                                        </td>

                                        <td className="p-4 text-[#71717A]">
                                            -
                                        </td>

                                        <td className="p-4">
                                            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 text-green-700 px-2.5 py-1 text-xs font-medium">
                                                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                                                Paid
                                            </span>
                                        </td>

                                        <td className="p-4 text-right relative">
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    setOpenMenuId(
                                                        openMenuId ===
                                                            structure.id
                                                            ? null
                                                            : structure.id
                                                    )
                                                }
                                                className="inline-flex items-center justify-center w-8 h-8 rounded-lg hover:bg-[#F4F4F5]"
                                            >
                                                <MoreHorizontal
                                                    size={18}
                                                    className="text-[#71717A]"
                                                />
                                            </button>

                                            {openMenuId === structure.id && (
                                                <div className="absolute right-4 top-12 z-30 w-36 bg-white border border-[#EEEEF2] rounded-lg shadow-lg py-1 text-left">
                                                    <button
                                                        type="button"
                                                        onClick={() => {
                                                            setViewingStructure(
                                                                structure
                                                            )
                                                            setOpenMenuId(null)
                                                        }}
                                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[#14142B] hover:bg-[#FAFAFA]"
                                                    >
                                                        <Eye size={15} />
                                                        View
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            openEditModal(
                                                                structure
                                                            )
                                                        }
                                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[#14142B] hover:bg-[#FAFAFA]"
                                                    >
                                                        <Pencil size={15} />
                                                        Edit
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            handleDelete(
                                                                structure.id
                                                            )
                                                        }
                                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                                                    >
                                                        <Trash2 size={15} />
                                                        Delete
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <div className="flex items-center justify-between p-4 border-t border-[#EEEEF2]">
                        <p className="text-xs text-[#A1A1AA]">
                            Showing {filteredStructures.length} of{' '}
                            {salaryStructures.length} employees
                        </p>

                        <p className="text-xs text-[#A1A1AA]">
                            Average salary:{' '}
                            <span className="font-medium text-[#3F3F46]">
                                {formatCurrency(averageSalary)}
                            </span>
                        </p>
                    </div>
                </div>
            )}

            {/* Add / Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-3xl bg-white rounded-2xl shadow-xl">
                        <div className="flex items-center justify-between p-5 border-b border-[#EEEEF2]">
                            <div>
                                <h2 className="text-lg font-semibold text-[#14142B]">
                                    {editingId
                                        ? 'Edit Salary Structure'
                                        : 'Add Salary Structure'}
                                </h2>

                                <p className="text-sm text-[#71717A] mt-1">
                                    Define salary allocation and allowance
                                    components.
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={resetForm}
                                className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-[#F4F4F5]"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit}>
                            <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[70vh] overflow-y-auto">
                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium text-[#14142B] mb-1.5">
                                        Employee
                                    </label>

                                    <select
                                        name="employee"
                                        value={form.employee}
                                        onChange={handleChange}
                                        required
                                        disabled={Boolean(editingId)}
                                        className="w-full border border-[#E4E4E7] rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#14142B] disabled:bg-[#F4F4F5]"
                                    >
                                        <option value="">
                                            Select Employee
                                        </option>

                                        {employees.map((employee) => (
                                            <option
                                                key={employee.id}
                                                value={employee.id}
                                            >
                                                {employee.employee_code} —{' '}
                                                {employee.email ||
                                                    employee.user?.email ||
                                                    'Employee'}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-[#14142B] mb-1.5">
                                        Base Salary
                                    </label>

                                    <input
                                        type="number"
                                        name="base_salary"
                                        value={form.base_salary}
                                        onChange={handleChange}
                                        placeholder="Enter base salary"
                                        min="0"
                                        step="0.01"
                                        required
                                        className="w-full border border-[#E4E4E7] rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#14142B]"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-[#14142B] mb-1.5">
                                        House Rent
                                    </label>

                                    <input
                                        type="number"
                                        name="house_rent"
                                        value={form.house_rent}
                                        onChange={handleChange}
                                        placeholder="Enter house rent"
                                        min="0"
                                        step="0.01"
                                        className="w-full border border-[#E4E4E7] rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#14142B]"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-[#14142B] mb-1.5">
                                        Medical
                                    </label>

                                    <input
                                        type="number"
                                        name="medical"
                                        value={form.medical}
                                        onChange={handleChange}
                                        placeholder="Enter medical allowance"
                                        min="0"
                                        step="0.01"
                                        className="w-full border border-[#E4E4E7] rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#14142B]"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-[#14142B] mb-1.5">
                                        Transport
                                    </label>

                                    <input
                                        type="number"
                                        name="transport"
                                        value={form.transport}
                                        onChange={handleChange}
                                        placeholder="Enter transport allowance"
                                        min="0"
                                        step="0.01"
                                        className="w-full border border-[#E4E4E7] rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#14142B]"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-[#14142B] mb-1.5">
                                        Other Allowances
                                    </label>

                                    <input
                                        type="number"
                                        name="other"
                                        value={form.other}
                                        onChange={handleChange}
                                        placeholder="Enter other allowance"
                                        min="0"
                                        step="0.01"
                                        className="w-full border border-[#E4E4E7] rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#14142B]"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-[#14142B] mb-1.5">
                                        Effective From
                                    </label>

                                    <input
                                        type="date"
                                        name="effective_from"
                                        value={form.effective_from}
                                        onChange={handleChange}
                                        required
                                        className="w-full border border-[#E4E4E7] rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#14142B]"
                                    />
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 p-5 border-t border-[#EEEEF2]">
                                <button
                                    type="button"
                                    onClick={resetForm}
                                    className="px-4 py-2.5 rounded-lg border border-[#E4E4E7] text-sm font-medium text-[#14142B] hover:bg-[#FAFAFA]"
                                >
                                    Cancel
                                </button>

                                <button
                                    type="submit"
                                    className="px-4 py-2.5 rounded-lg bg-[#14142B] text-white text-sm font-medium hover:opacity-90"
                                >
                                    {editingId
                                        ? 'Update Structure'
                                        : 'Save Structure'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* View Modal */}
            {viewingStructure && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl">
                        <div className="flex items-center justify-between p-5 border-b border-[#EEEEF2]">
                            <div>
                                <h2 className="text-lg font-semibold text-[#14142B]">
                                    Salary Structure Details
                                </h2>

                                <p className="text-sm text-[#71717A] mt-1">
                                    Employee salary allocation details.
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={() => setViewingStructure(null)}
                                className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-[#F4F4F5]"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="p-5 space-y-5">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="bg-[#FAFAFA] rounded-xl p-4">
                                    <p className="text-xs text-[#71717A]">
                                        Employee
                                    </p>

                                    <p className="font-medium text-[#14142B] mt-1">
                                        {viewingStructure.employee_name}
                                    </p>
                                </div>

                                <div className="bg-[#FAFAFA] rounded-xl p-4">
                                    <p className="text-xs text-[#71717A]">
                                        Employee ID
                                    </p>

                                    <p className="font-medium text-[#14142B] mt-1">
                                        {viewingStructure.employee_code}
                                    </p>
                                </div>

                                <div className="bg-[#FAFAFA] rounded-xl p-4">
                                    <p className="text-xs text-[#71717A]">
                                        Position
                                    </p>

                                    <p className="font-medium text-[#14142B] mt-1">
                                        {getEmployeePosition(
                                            viewingStructure
                                        )}
                                    </p>
                                </div>

                                <div className="bg-[#FAFAFA] rounded-xl p-4">
                                    <p className="text-xs text-[#71717A]">
                                        Base Salary
                                    </p>

                                    <p className="font-semibold text-[#14142B] mt-1">
                                        {formatCurrency(
                                            viewingStructure.base_salary
                                        )}
                                    </p>
                                </div>

                                <div className="bg-[#FAFAFA] rounded-xl p-4">
                                    <p className="text-xs text-[#71717A]">
                                        Gross Salary
                                    </p>

                                    <p className="font-semibold text-[#14142B] mt-1">
                                        {formatCurrency(
                                            getGrossSalary(viewingStructure)
                                        )}
                                    </p>
                                </div>

                                <div className="bg-[#FAFAFA] rounded-xl p-4">
                                    <p className="text-xs text-[#71717A]">
                                        Effective From
                                    </p>

                                    <p className="font-medium text-[#14142B] mt-1">
                                        {viewingStructure.effective_from}
                                    </p>
                                </div>
                            </div>

                            <div>
                                <h3 className="font-medium text-[#14142B] mb-3">
                                    Allowances
                                </h3>

                                <div className="border border-[#EEEEF2] rounded-xl overflow-hidden">
                                    {Object.entries(
                                        viewingStructure.allowances || {}
                                    ).map(([key, value]) => (
                                        <div
                                            key={key}
                                            className="flex items-center justify-between px-4 py-3 border-b last:border-b-0 border-[#F4F4F5]"
                                        >
                                            <span className="text-sm text-[#71717A] capitalize">
                                                {key.replaceAll('_', ' ')}
                                            </span>

                                            <span className="text-sm font-medium text-[#14142B]">
                                                {formatCurrency(value)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="flex justify-end p-5 border-t border-[#EEEEF2]">
                            <button
                                type="button"
                                onClick={() => setViewingStructure(null)}
                                className="px-4 py-2.5 rounded-lg bg-[#14142B] text-white text-sm font-medium"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default SalaryStructuresPage

