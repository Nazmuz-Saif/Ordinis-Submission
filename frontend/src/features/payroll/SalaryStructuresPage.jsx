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

    const filteredStructures = useMemo(() => {
        const query = search.trim().toLowerCase()

        if (!query) {
            return salaryStructures
        }

        return salaryStructures.filter((structure) => {
            return (
                structure.employee_name?.toLowerCase().includes(query) ||
                structure.employee_code?.toLowerCase().includes(query) ||
                String(structure.base_salary || '').includes(query)
            )
        })
    }, [salaryStructures, search])

    const totalPayroll = salaryStructures.reduce(
        (total, structure) => total + getGrossSalary(structure),
        0
    )

    if (!canManageSalary) {
        return (
            <div className="min-h-full">
                <div className="bg-white rounded-xl border border-[#EEEEF2] p-6">
                    <h1 className="text-2xl font-bold text-[#14142B]">
                        Salary Structures
                    </h1>

                    <p className="text-sm text-[#71717A] mt-2">
                        You do not have permission to view salary information.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-full">
            {/* Header */}
            <div className="flex flex-col gap-5 mb-6">
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-[#14142B]">
                            Salary Structures
                        </h1>

                        <p className="text-sm text-[#71717A] mt-1">
                            Salary structures are pre-defined salary allocations
                            for employees.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={openCreateModal}
                        className="inline-flex items-center gap-2 bg-[#14142B] text-white rounded-lg px-4 py-2.5 text-sm font-medium hover:opacity-90"
                    >
                        <Plus size={17} />
                        Add Structure
                    </button>
                </div>

                {/* Search */}
                <div className="flex items-center justify-between gap-4">
                    <div className="relative w-full max-w-md">
                        <Search
                            size={17}
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1AA]"
                        />

                        <input
                            type="text"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search structures..."
                            className="w-full border border-[#E4E4E7] rounded-lg pl-10 pr-4 py-2.5 text-sm outline-none focus:border-[#14142B]"
                        />
                    </div>

                    <div className="flex items-center gap-2 text-sm text-[#71717A]">
                        <DollarSign size={17} />
                        Finance
                    </div>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 rounded-xl p-3 mb-6 text-sm">
                    {error}
                </div>
            )}

            {/* Summary cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white rounded-xl border border-[#EEEEF2] p-5">
                    <p className="text-sm text-[#71717A]">
                        Salary Structures
                    </p>

                    <p className="text-2xl font-bold text-[#14142B] mt-1">
                        {salaryStructures.length}
                    </p>

                    <p className="text-xs text-[#A1A1AA] mt-1">
                        Active structures
                    </p>
                </div>

                <div className="bg-white rounded-xl border border-[#EEEEF2] p-5">
                    <p className="text-sm text-[#71717A]">
                        Employees Assigned
                    </p>

                    <p className="text-2xl font-bold text-[#14142B] mt-1">
                        {salaryStructures.length}
                    </p>

                    <p className="text-xs text-[#A1A1AA] mt-1">
                        Employees with salary structure
                    </p>
                </div>

                <div className="bg-white rounded-xl border border-[#EEEEF2] p-5">
                    <p className="text-sm text-[#71717A]">
                        Total Payroll
                    </p>

                    <p className="text-2xl font-bold text-[#14142B] mt-1">
                        {totalPayroll.toLocaleString()}
                    </p>

                    <p className="text-xs text-[#A1A1AA] mt-1">
                        Gross salary total
                    </p>
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl border border-[#EEEEF2] overflow-visible">
                <div className="flex items-center justify-between p-4 border-b border-[#EEEEF2]">
                    <div>
                        <h2 className="font-semibold text-[#14142B]">
                            Salary Structures
                        </h2>

                        <p className="text-xs text-[#A1A1AA] mt-1">
                            Manage employee salary allocation and allowances.
                        </p>
                    </div>

                    <span className="text-xs text-[#71717A]">
                        {filteredStructures.length} result
                        {filteredStructures.length !== 1 ? 's' : ''}
                    </span>
                </div>

                {loading ? (
                    <div className="p-8 text-center text-sm text-[#71717A]">
                        Loading salary structures...
                    </div>
                ) : filteredStructures.length === 0 ? (
                    <div className="p-10 text-center">
                        <DollarSign
                            size={32}
                            className="mx-auto text-[#A1A1AA] mb-3"
                        />

                        <h3 className="font-medium text-[#14142B]">
                            No salary structures found
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
                                className="mt-4 inline-flex items-center gap-2 bg-[#14142B] text-white rounded-lg px-4 py-2 text-sm font-medium"
                            >
                                <Plus size={16} />
                                Add Structure
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left border-b border-[#EEEEF2] bg-[#FAFAFA]">
                                    <th className="p-4 font-medium text-[#71717A]">
                                        Structure Name
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Employee
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Components
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Base Salary
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Gross Salary
                                    </th>

                                    <th className="p-4 font-medium text-[#71717A]">
                                        Effective From
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
                                {filteredStructures.map((structure) => {
                                    const allowances = structure.allowances || {}

                                    const componentCount = Object.values(
                                        allowances
                                    ).filter(
                                        (value) => Number(value || 0) > 0
                                    ).length

                                    return (
                                        <tr
                                            key={structure.id}
                                            className="border-b border-[#F4F4F5] hover:bg-[#FAFAFA]"
                                        >
                                            <td className="p-4">
                                                <div className="font-medium text-[#14142B]">
                                                    Salary Structure
                                                </div>

                                                <div className="text-xs text-[#A1A1AA] mt-1">
                                                    #{structure.id}
                                                </div>
                                            </td>

                                            <td className="p-4">
                                                <div className="font-medium text-[#14142B]">
                                                    {structure.employee_name}
                                                </div>

                                                <div className="text-xs text-[#71717A] mt-1">
                                                    {structure.employee_code}
                                                </div>
                                            </td>

                                            <td className="p-4 text-[#71717A]">
                                                <span className="inline-flex items-center rounded-full bg-[#F4F4F5] px-2.5 py-1 text-xs font-medium">
                                                    {componentCount + 1} items
                                                </span>
                                            </td>

                                            <td className="p-4 text-[#14142B] font-medium">
                                                {Number(
                                                    structure.base_salary || 0
                                                ).toLocaleString()}
                                            </td>

                                            <td className="p-4 text-[#14142B] font-semibold">
                                                {getGrossSalary(
                                                    structure
                                                ).toLocaleString()}
                                            </td>

                                            <td className="p-4 text-[#71717A]">
                                                {structure.effective_from}
                                            </td>

                                            <td className="p-4">
                                                <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 text-green-700 px-2.5 py-1 text-xs font-medium">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                                                    Active
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

                                                {openMenuId ===
                                                    structure.id && (
                                                        <div className="absolute right-4 top-12 z-20 w-36 bg-white border border-[#EEEEF2] rounded-lg shadow-lg py-1 text-left">
                                                            <button
                                                                type="button"
                                                                onClick={() => {
                                                                    setViewingStructure(
                                                                        structure
                                                                    )
                                                                    setOpenMenuId(
                                                                        null
                                                                    )
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
                                                                <Pencil
                                                                    size={15}
                                                                />
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
                                                                <Trash2
                                                                    size={15}
                                                                />
                                                                Delete
                                                            </button>
                                                        </div>
                                                    )}
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

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
                                        Base Salary
                                    </p>

                                    <p className="font-semibold text-[#14142B] mt-1">
                                        {Number(
                                            viewingStructure.base_salary || 0
                                        ).toLocaleString()}
                                    </p>
                                </div>

                                <div className="bg-[#FAFAFA] rounded-xl p-4">
                                    <p className="text-xs text-[#71717A]">
                                        Gross Salary
                                    </p>

                                    <p className="font-semibold text-[#14142B] mt-1">
                                        {getGrossSalary(
                                            viewingStructure
                                        ).toLocaleString()}
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
                                                {Number(
                                                    value || 0
                                                ).toLocaleString()}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="flex items-center justify-between text-sm">
                                <span className="text-[#71717A]">
                                    Effective From
                                </span>

                                <span className="font-medium text-[#14142B]">
                                    {viewingStructure.effective_from}
                                </span>
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