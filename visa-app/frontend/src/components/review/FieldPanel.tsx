import type {
  ApplicationReviewField,
  CaseData,
  FieldMetadataMap,
  MissingRequiredField,
  Review,
} from '../../types/caseData'
import FieldSection from './FieldSection'
import FieldRow from './FieldRow'
import RepeatedFieldGroup from './RepeatedFieldGroup'
import {
  flattenCaseData,
  getByPath,
  getFieldInput,
  getFieldLabel,
  getReviewFieldInput,
  getSectionForPath,
  REVIEW_FIELD_PATHS,
  SECTION_ORDER,
  SYSTEM_REVIEW_FIELD_PREFIXES,
} from '../../lib/fieldPaths'
import { getReviewFieldOrder } from '../../lib/reviewFieldOrder'

interface Props {
  caseData: CaseData
  targetStatus: string
  fieldMetadata: FieldMetadataMap
  review: Review
  reviewFields?: ApplicationReviewField[]
  missingRequiredFields?: MissingRequiredField[]
  pendingManualFields?: MissingRequiredField[]
  onFieldUpdate: (fieldPath: string, value: string) => void
}

interface DisplayField {
  path: string
  value: unknown
  label?: string
  section?: string
  input?: ReturnType<typeof getFieldInput>
  required?: boolean
  manualRequired?: boolean
  rasensOnly?: boolean
  issueReason?: string
}

const REPEATED_FIELD_PREFIXES = [
  'applicant.family.japan_relatives_or_cohabitants.',
  'applicant.employment_history.',
]

const JAPAN_RELATIVE_FIELDS = [
  { path: 'relationship' },
  { path: 'name' },
  { path: 'birth_date' },
  { path: 'nationality_region' },
  { path: 'will_cohabit' },
  { path: 'workplace_or_school_name' },
  { path: 'residence_card_or_certificate_number' },
]

const EMPLOYMENT_HISTORY_FIELDS = [
  { path: 'country_region' },
  { path: 'start_month_unknown' },
  { path: 'start_date' },
  { path: 'end_month_unknown' },
  { path: 'end_date' },
  { path: 'company_name_en' },
  { path: 'company_name_local' },
]

function isRepeatedDetailPath(path: string): boolean {
  return REPEATED_FIELD_PREFIXES.some((prefix) => path.startsWith(prefix))
}

function isFixedSettingsPath(path: string): boolean {
  return path.startsWith('settings.')
}

function isSystemReviewField(path: string): boolean {
  return SYSTEM_REVIEW_FIELD_PREFIXES.some((prefix) => path.startsWith(prefix))
}

function isCaseRoutingPath(path: string): boolean {
  return [
    'case.application_type',
    'case.target_status',
    'case.target_status_variant',
  ].includes(path)
}

function reviewFieldPath(field: ApplicationReviewField | MissingRequiredField): string {
  return field.canonical_path || ''
}

function isRasensOnlyManualField(field: ApplicationReviewField | MissingRequiredField, path: string): boolean {
  const inputType = field.input_type?.toLowerCase()
  return (
    inputType === 'file' ||
    path === 'specified_skilled_worker.application.applicant_intent_confirmed' ||
    path === 'specified_skilled_worker.application.content_confirmed' ||
    path === 'specified_skilled_worker.application.photo_file'
  )
}

function isTruthy(value: unknown): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value === 1
  if (typeof value === 'string') {
    return ['true', 'yes', '有', 'あり', '有 yes', '1'].includes(value.trim().toLowerCase())
  }
  return false
}

function issuePath(item: unknown): string | null {
  if (typeof item === 'object' && item !== null && 'path' in item) {
    const path = (item as { path?: unknown }).path
    return typeof path === 'string' && path ? path : null
  }
  if (typeof item === 'string' && item.includes('.') && !/\s/.test(item)) {
    return item
  }
  return null
}

export default function FieldPanel({
  caseData,
  targetStatus,
  fieldMetadata,
  review,
  reviewFields = [],
  missingRequiredFields = [],
  pendingManualFields = [],
  onFieldUpdate,
}: Props) {
  const reviewPaths = new Set(
    [...reviewFields, ...missingRequiredFields, ...pendingManualFields]
      .map(reviewFieldPath)
      .filter((path) => path && !isSystemReviewField(path)),
  )
  const fields: DisplayField[] = flattenCaseData(caseData).filter(
    (field) => field.path !== 'case.workflow_state' && !isRepeatedDetailPath(field.path),
  )

  // Build set of flagged paths
  const missingPaths = new Set(
    review.missing_items?.map(issuePath).filter((path): path is string => Boolean(path)) ?? [],
  )
  const errorPaths = new Set(
    review.validation_errors?.map(issuePath).filter((path): path is string => Boolean(path)) ?? [],
  )
  const visibleFields = targetStatus === 'specified_skilled_worker'
    ? fields.filter((field) => field.path.startsWith('case.') || reviewPaths.has(field.path))
    : [...fields]
  const existingPaths = new Set(visibleFields.map((field) => field.path))
  const reviewFieldByPath = new Map<string, ApplicationReviewField>()
  const missingReasonByPath = new Map<string, string>()

  for (const field of reviewFields) {
    const path = reviewFieldPath(field)
    if (!path || isSystemReviewField(path)) continue
    reviewFieldByPath.set(path, field)
  }
  for (const field of missingRequiredFields) {
    const path = reviewFieldPath(field)
    if (!path || isSystemReviewField(path)) continue
    reviewFieldByPath.set(path, { ...reviewFieldByPath.get(path), ...field })
    if (field.reason) missingReasonByPath.set(path, field.reason)
  }
  for (const field of pendingManualFields) {
    const path = reviewFieldPath(field)
    if (!path || isSystemReviewField(path)) continue
    reviewFieldByPath.set(path, {
      ...reviewFieldByPath.get(path),
      ...field,
      manual_required: true,
    })
    if (field.reason) missingReasonByPath.set(path, field.reason)
  }

  if (targetStatus !== 'specified_skilled_worker') {
    for (const path of REVIEW_FIELD_PATHS) {
      if (!existingPaths.has(path)) {
        visibleFields.push({ path, value: getByPath(caseData, path) })
        existingPaths.add(path)
      }
    }
  }
  for (const path of [...missingPaths, ...errorPaths]) {
    if (!existingPaths.has(path)) {
      visibleFields.push({ path, value: undefined })
      existingPaths.add(path)
    }
  }
  for (const [path, field] of reviewFieldByPath.entries()) {
    if (!existingPaths.has(path)) {
      visibleFields.push({
        path,
        value: getByPath(caseData, path),
        label: field.label,
        section: field.section,
        input: getReviewFieldInput(field),
        required: field.required,
        manualRequired: field.manual_required,
        rasensOnly: isRasensOnlyManualField(field, path),
        issueReason: missingReasonByPath.get(path),
      })
      existingPaths.add(path)
    }
  }
  for (const field of visibleFields) {
    const reviewField = reviewFieldByPath.get(field.path)
    if (!reviewField) continue
    field.label ??= reviewField.label
    field.section ??= reviewField.section
    field.input ??= getReviewFieldInput(reviewField)
    field.required ??= reviewField.required
    field.manualRequired ??= reviewField.manual_required
    field.rasensOnly ??= isRasensOnlyManualField(reviewField, field.path)
    field.issueReason ??= missingReasonByPath.get(field.path)
  }

  // Group by section
  const sections = new Map<string, DisplayField[]>()
  for (const field of visibleFields) {
    const section = field.section || getSectionForPath(field.path)
    if (!sections.has(section)) sections.set(section, [])
    sections.get(section)!.push(field)
  }
  for (const sectionFields of sections.values()) {
    sectionFields.sort((a, b) => (
      getReviewFieldOrder(a.path) - getReviewFieldOrder(b.path)
      || a.path.localeCompare(b.path)
    ))
  }
  const hasManualRequiredField = visibleFields.some((field) => field.manualRequired)

  // Sort sections by SECTION_ORDER; unknown sections go to the end
  const sortedSections = Array.from(sections.entries()).sort(([a], [b]) => {
    const ai = (SECTION_ORDER as readonly string[]).indexOf(a)
    const bi = (SECTION_ORDER as readonly string[]).indexOf(b)
    return (ai === -1 ? SECTION_ORDER.length : ai) - (bi === -1 ? SECTION_ORDER.length : bi)
  })

  return (
    <div data-field-panel>
      {hasManualRequiredField && (
        <div className="mx-4 mt-4 rounded-lg border border-purple-200 bg-purple-50 px-3 py-2 text-xs text-purple-800">
          「人確認」は、資料からAIだけで確定せず、担当者がレビュー画面またはRASENS上で確認・入力する項目です。
        </div>
      )}
      {sortedSections.map(([section, sectionFields]) => {
        return (
          <FieldSection
            key={section}
            title={section}
            fieldCount={sectionFields.length}
          >
            {sectionFields.map((f) => (
              <div key={f.path}>
                <FieldRow
                  label={f.label || getFieldLabel(f.path)}
                  fieldPath={f.path}
                  value={f.value}
                  input={f.input || getFieldInput(f.path)}
                  meta={fieldMetadata[f.path]}
                  onUpdate={onFieldUpdate}
                  readOnly={isFixedSettingsPath(f.path) || isCaseRoutingPath(f.path) || f.rasensOnly}
                  required={f.required}
                  manualRequired={f.manualRequired}
                  rasensOnly={f.rasensOnly}
                  issueReason={f.issueReason}
                />
                {f.path === 'applicant.family.has_japan_relatives_or_cohabitants' && (
                  <RepeatedFieldGroup
                    title="在日親族・同居者 詳細"
                    itemLabel="親族・同居者"
                    basePath="applicant.family.japan_relatives_or_cohabitants"
                    maxItems={3}
                    fields={JAPAN_RELATIVE_FIELDS}
                    enabled={isTruthy(getByPath(caseData, 'applicant.family.has_japan_relatives_or_cohabitants'))}
                    caseData={caseData}
                    fieldMetadata={fieldMetadata}
                    onFieldUpdate={onFieldUpdate}
                  />
                )}
                {f.path === 'applicant.has_employment_history' && (
                  <RepeatedFieldGroup
                    title="職歴 詳細"
                    itemLabel="職歴"
                    basePath="applicant.employment_history"
                    maxItems={3}
                    fields={EMPLOYMENT_HISTORY_FIELDS}
                    enabled={isTruthy(getByPath(caseData, 'applicant.has_employment_history'))}
                    caseData={caseData}
                    fieldMetadata={fieldMetadata}
                    onFieldUpdate={onFieldUpdate}
                  />
                )}
              </div>
            ))}
          </FieldSection>
        )
      })}
    </div>
  )
}
