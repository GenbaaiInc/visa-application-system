import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { ApplicationType, CreateCaseParams, TargetStatus, TargetStatusVariant } from '../../types/caseData'

const applicationTypes: { value: ApplicationType; label: string; description: string }[] = [
  {
    value: 'certificate_of_eligibility',
    label: '認定・COE',
    description: '海外から呼ぶ新規入国',
  },
  {
    value: 'change_of_status',
    label: '変更',
    description: '日本国内で在留資格を変える',
  },
  {
    value: 'extension_of_stay',
    label: '更新',
    description: '今の在留期間を延ばす',
  },
]

const targetStatuses: { value: TargetStatus; label: string; description: string }[] = [
  {
    value: 'engineer_humanities_international',
    label: '技術・人文知識・国際業務',
    description: 'COEのみAI抽出・RASENS入力に対応',
  },
  {
    value: 'specified_skilled_worker',
    label: '特定技能',
    description: '認定・変更・更新に対応',
  },
]

const sswVariants: { value: TargetStatusVariant; label: string }[] = [
  { value: 'ssw_1', label: '1号' },
  { value: 'ssw_2', label: '2号' },
]

interface CreateCaseDialogProps {
  open: boolean
  onCancel: () => void
  onCreate: (params: CreateCaseParams) => Promise<void>
}

export default function CreateCaseDialog({ open, onCancel, onCreate }: CreateCaseDialogProps) {
  const [applicationType, setApplicationType] = useState<ApplicationType>('certificate_of_eligibility')
  const [targetStatus, setTargetStatus] = useState<TargetStatus>('engineer_humanities_international')
  const [targetStatusVariant, setTargetStatusVariant] = useState<TargetStatusVariant>('ssw_1')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setApplicationType('certificate_of_eligibility')
    setTargetStatus('engineer_humanities_international')
    setTargetStatusVariant('ssw_1')
    setSubmitting(false)
    setError(null)
  }, [open])

  if (!open) return null

  const supported =
    targetStatus === 'specified_skilled_worker' ||
    applicationType === 'certificate_of_eligibility'

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!supported) return
    setSubmitting(true)
    setError(null)
    try {
      await onCreate({
        application_type: applicationType,
        target_status: targetStatus,
        target_status_variant:
          targetStatus === 'specified_skilled_worker' ? targetStatusVariant : undefined,
      })
    } catch {
      setError('案件を作成できませんでした。もう一度お試しください。')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-case-title"
        className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl"
      >
        <form onSubmit={handleSubmit}>
          <h2 id="create-case-title" className="text-lg font-semibold text-gray-900">
            新規案件
          </h2>
          <p className="mt-1 text-sm text-gray-500">手続きと在留資格を選択してください。</p>

          <fieldset className="mt-5">
            <legend className="text-sm font-medium text-gray-700">手続き</legend>
            <div className="grid gap-3 sm:grid-cols-3">
              {applicationTypes.map((option, index) => {
                const selected = applicationType === option.value
                return (
                  <label
                    key={option.value}
                    className={`cursor-pointer rounded-lg border p-4 transition-colors focus-within:ring-2 focus-within:ring-blue-500 ${
                      selected ? 'border-blue-600 bg-blue-50' : 'border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="application-type"
                      value={option.value}
                      checked={selected}
                      onChange={() => setApplicationType(option.value)}
                      autoFocus={index === 0}
                      className="sr-only"
                    />
                    <span className="block text-sm font-medium text-gray-900">{option.label}</span>
                    <span className="mt-1 block text-xs text-gray-500">{option.description}</span>
                  </label>
                )
              })}
            </div>
          </fieldset>

          <fieldset className="mt-5">
            <legend className="text-sm font-medium text-gray-700">対象の在留資格</legend>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              {targetStatuses.map((option) => {
                const selected = targetStatus === option.value
                return (
                  <label
                    key={option.value}
                    className={`cursor-pointer rounded-lg border p-4 transition-colors focus-within:ring-2 focus-within:ring-blue-500 ${
                      selected ? 'border-blue-600 bg-blue-50' : 'border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="target-status"
                      value={option.value}
                      checked={selected}
                      onChange={() => setTargetStatus(option.value)}
                      className="sr-only"
                    />
                    <span className="block text-sm font-medium text-gray-900">{option.label}</span>
                    <span className="mt-1 block text-xs text-gray-500">{option.description}</span>
                  </label>
                )
              })}
            </div>
          </fieldset>

          {targetStatus === 'specified_skilled_worker' && (
            <fieldset className="mt-5">
              <legend className="text-sm font-medium text-gray-700">特定技能区分</legend>
              <div className="mt-2 flex gap-3">
                {sswVariants.map((option) => (
                  <label
                    key={option.value}
                    className={`cursor-pointer rounded-lg border px-4 py-2 text-sm transition-colors focus-within:ring-2 focus-within:ring-blue-500 ${
                      targetStatusVariant === option.value
                        ? 'border-blue-600 bg-blue-50 text-blue-900'
                        : 'border-gray-200 text-gray-700 hover:border-blue-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="target-status-variant"
                      value={option.value}
                      checked={targetStatusVariant === option.value}
                      onChange={() => setTargetStatusVariant(option.value)}
                      className="sr-only"
                    />
                    {option.label}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {!supported && (
            <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              技人国の変更・更新はまだ未対応です。まずはCOEを選択してください。
            </p>
          )}

          {targetStatus === 'specified_skilled_worker' && (
            <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              特定技能はCOE・変更・更新の案件作成に対応します。抽出・RASENS入力は対応済みの組合せから利用できます。
            </p>
          )}

          {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}

          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={submitting}
              className="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-50"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={submitting || !supported}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300"
            >
              {submitting ? '作成中...' : '作成'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
