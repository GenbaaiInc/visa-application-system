import CopyableCaseId from '../common/CopyableCaseId'
import { getDisplayValue, getTargetStatusDisplayValue } from '../../lib/fieldPaths'
import { toWorkflowDisplayState, workflowStateColor, workflowStateLabel } from '../../lib/workflowState'

interface Props {
  caseId: string
  workflowState: string
  applicationType?: string
  targetStatus: string
  targetStatusVariant?: string
}

export default function ReviewBanner({
  caseId,
  workflowState,
  applicationType,
  targetStatus,
  targetStatusVariant,
}: Props) {
  const displayState = toWorkflowDisplayState(workflowState)
  const targetStatusLabel = getTargetStatusDisplayValue(targetStatus, targetStatusVariant)

  return (
    <div className="bg-white border-b border-gray-200">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-2.5 text-sm sm:px-6">
        <CopyableCaseId
          caseId={caseId}
          className="text-gray-500 text-xs"
          feedbackClassName="text-xs"
        />
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${workflowStateColor[displayState]}`}>
          {workflowStateLabel[displayState]}
        </span>
        {applicationType && (
          <span className="text-xs text-gray-700">
            手続き: {getDisplayValue(applicationType)}
          </span>
        )}
        <span className="text-xs text-gray-700">
          対象の在留資格: {targetStatusLabel}
        </span>
        {targetStatus === 'specified_skilled_worker' && (
          <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 text-xs font-medium">
            未確認の申告項目は手入力
          </span>
        )}
        {displayState === 'extracted' && targetStatus !== 'specified_skilled_worker' && (
          <span className="text-xs text-gray-500">抽出結果を確認・編集できます</span>
        )}
      </div>
    </div>
  )
}
