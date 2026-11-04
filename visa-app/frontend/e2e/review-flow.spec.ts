import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

async function openCreateCaseDialog(page: Page) {
  await page.goto('/?demo=true')
  await page.getByRole('button', { name: '+ 新規案件' }).click()
  await expect(page.getByRole('dialog', { name: '新規案件' })).toBeVisible()
}

async function createSpecifiedSkilledWorkerCase(
  page: Page,
  applicationType: '認定・COE' | '変更' | '更新',
  variant: '1号' | '2号' = '1号',
) {
  const applicationTypeValue = {
    '認定・COE': 'certificate_of_eligibility',
    '変更': 'change_of_status',
    '更新': 'extension_of_stay',
  }[applicationType]
  const variantValue = variant === '1号' ? 'ssw_1' : 'ssw_2'

  await openCreateCaseDialog(page)
  await page.locator(`input[name="application-type"][value="${applicationTypeValue}"]`).check({ force: true })
  await page.locator('input[name="target-status"][value="specified_skilled_worker"]').check({ force: true })
  await page.locator(`input[name="target-status-variant"][value="${variantValue}"]`).check({ force: true })
  await page.getByRole('button', { name: '作成' }).click()
  await expect(page).toHaveURL(/\/cases\/demo-gijinkoku-001\/upload\?demo=true/)
}

test.describe('CaseListPage', () => {
  test('displays heading and new case button in Japanese', async ({ page }) => {
    await page.goto('/?demo=true')
    await expect(page.getByRole('heading', { name: '案件一覧' })).toBeVisible()
    await expect(page.getByRole('button', { name: '+ 新規案件' })).toBeVisible()
    await expect(page.getByText('抽出済み')).toBeVisible()
  })

  test('copies case_id without opening the case', async ({ page }) => {
    await page.goto('/?demo=true')
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'], {
      origin: new URL(page.url()).origin,
    })

    await page.getByRole('button', { name: 'demo-gijinkoku-001 をコピー' }).click()

    await expect(page).toHaveURL(/\?demo=true/)
    await expect(page.getByText('コピー済')).toBeVisible()
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe('demo-gijinkoku-001')
  })
})

test.describe('CreateCaseDialog application workflows', () => {
  for (const [applicationType, expectedLabel] of [
    ['認定・COE', '在留資格認定証明書交付申請'],
    ['変更', '在留資格変更許可申請'],
    ['更新', '在留期間更新許可申請'],
  ] as const) {
    test(`creates specified skilled worker ${applicationType} case`, async ({ page }) => {
      await createSpecifiedSkilledWorkerCase(page, applicationType)
      await expect(page.getByText(`手続き: ${expectedLabel}`)).toBeVisible()
      await expect(page.getByText('対象の在留資格: 特定技能1号')).toBeVisible()
    })
  }

  test('creates engineer/humanities COE case', async ({ page }) => {
    await openCreateCaseDialog(page)
    await page.locator('input[name="application-type"][value="certificate_of_eligibility"]').check({ force: true })
    await page.locator('input[name="target-status"][value="engineer_humanities_international"]').check({ force: true })
    await page.getByRole('button', { name: '作成' }).click()

    await expect(page).toHaveURL(/\/cases\/demo-gijinkoku-001\/upload\?demo=true/)
    await expect(page.getByText('手続き: 在留資格認定証明書交付申請')).toBeVisible()
    await expect(page.getByText('対象の在留資格: 技術・人文知識・国際業務')).toBeVisible()
  })

  for (const applicationType of ['変更', '更新'] as const) {
    test(`keeps engineer/humanities ${applicationType} creation disabled`, async ({ page }) => {
      await openCreateCaseDialog(page)
      const applicationTypeValue = applicationType === '変更' ? 'change_of_status' : 'extension_of_stay'
      await page.locator(`input[name="application-type"][value="${applicationTypeValue}"]`).check({ force: true })
      await page.locator('input[name="target-status"][value="engineer_humanities_international"]').check({ force: true })

      await expect(page.getByText('技人国の変更・更新はまだ未対応です。まずはCOEを選択してください。')).toBeVisible()
      await expect(page.getByRole('button', { name: '作成' })).toBeDisabled()
    })
  }
})

test.describe('Specified skilled worker review fields', () => {
  test('required review fields can be edited and are refreshed after save', async ({ page }) => {
    await createSpecifiedSkilledWorkerCase(page, '認定・COE')
    await page.getByRole('button', { name: '抽出開始' }).click()
    await expect(page).toHaveURL(/\/cases\/demo-gijinkoku-001\/review/)

    await expect(page.getByText('対象の在留資格: 特定技能1号')).toBeVisible()
    await expect(page.getByText('「人確認」は、資料からAIだけで確定せず')).toBeVisible()
    await expect(page.getByText('特定技能では雇用形態の確認が必要です。')).toBeVisible()
    await expect(page.getByText('1号の場合は支援方法の確認が必要です。')).toBeVisible()

    const employmentRow = page.locator('[data-field-row]').filter({ hasText: '雇用形態' })
    await employmentRow.dblclick()
    await employmentRow.locator('select').selectOption('direct')
    await employmentRow.getByRole('button', { name: '保存' }).click()
    await expect(employmentRow).toContainText('直接雇用')

    const supportRow = page.locator('[data-field-row]').filter({ hasText: '支援方法' })
    await supportRow.dblclick()
    await supportRow.locator('select').selectOption('entrusted')
    await supportRow.getByRole('button', { name: '保存' }).click()
    await expect(supportRow).toContainText('登録支援機関へ委託')

    await page.locator('.border-t').getByRole('button', { name: '保存' }).click()

    await expect(page.getByText('保存しました')).toBeVisible()
    await expect(page.getByText('特定技能では雇用形態の確認が必要です。')).not.toBeVisible()
    await expect(page.getByText('1号の場合は支援方法の確認が必要です。')).not.toBeVisible()
    await expect(page.getByText('支援計画の最終確認')).toBeVisible()
  })
})

test.describe('ReviewPage demo mode', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/cases/demo/review?demo=true')
  })

  test('shows ReviewBanner with case_id', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'demo-gijinkoku-001 をコピー' })).toBeVisible()
    await expect(page.getByText('抽出済み')).toBeVisible()
  })

  test('shows at least one FieldSection', async ({ page }) => {
    await expect(page.locator('[data-field-row]').first()).toBeVisible()
    await expect(page.getByText('身分事項')).toBeVisible()
  })

  test('shows FieldRows inside sections', async ({ page }) => {
    const fieldRows = page.locator('[data-field-row]')
    await expect(fieldRows.first()).toBeVisible()
    const count = await fieldRows.count()
    expect(count).toBeGreaterThanOrEqual(1)
  })

  test('does not show review progress controls', async ({ page }) => {
    await expect(page.locator('[data-field-row]').first()).toBeVisible()
    await expect(page.getByText('確認済:')).not.toBeVisible()
    await expect(page.getByText('要対応')).not.toBeVisible()
    await expect(page.getByText('編集済')).not.toBeVisible()
    await expect(page.getByText('要レビュー')).not.toBeVisible()
    await expect(page.getByText('位置候補')).not.toBeVisible()
    await expect(page.getByText('未確認候補')).not.toBeVisible()
    await expect(page.getByRole('button', { name: '全て確認済み' })).not.toBeVisible()
    await expect(page.getByRole('button', { name: '確認して完了' })).not.toBeVisible()
    await expect(page.getByRole('button', { name: '保存' })).toBeVisible()
  })

  test('clicking a FieldRow activates it', async ({ page }) => {
    const firstRow = page.locator('[data-field-row]').first()
    await firstRow.click()
    await expect(firstRow).toHaveClass(/bg-blue-100/)
  })

  test('inline edit: double-click to edit, save updates value', async ({ page }) => {
    const firstRow = page.locator('[data-field-row]').filter({ hasText: '氏名（ローマ字）' })
    await expect(firstRow).toBeVisible()

    // Double-click to enter edit mode
    await firstRow.dblclick()

    // Edit input should appear
    const input = firstRow.locator('input')
    await expect(input).toBeVisible()

    // Clear and type new value
    await input.fill('テスト編集値')

    // Click save button
    await firstRow.getByRole('button', { name: '保存' }).click()

    // Input should disappear and new value should be displayed
    await expect(input).not.toBeVisible()
    await expect(firstRow.getByText('テスト編集値')).toBeVisible()

    await expect(firstRow.locator('span').filter({ hasText: '編集済' })).not.toBeVisible()
  })

  test('keyboard: Enter to edit, Escape to cancel', async ({ page }) => {
    const firstRow = page.locator('[data-field-row]').filter({ hasText: '氏名（ローマ字）' })
    await expect(firstRow).toBeVisible()

    // Focus the row
    await firstRow.focus()

    // Press Enter to start editing
    await page.keyboard.press('Enter')
    const input = firstRow.locator('input')
    await expect(input).toBeVisible()

    // Press Escape to cancel
    await page.keyboard.press('Escape')
    await expect(input).not.toBeVisible()
  })

  test('organization settings are displayed as fixed and cannot be edited', async ({ page }) => {
    const fixedSettingRows = page.locator('[data-field-row][data-read-only="true"]')
    const organizationSettingRows = fixedSettingRows.filter({
      hasText: /取次者|受領方法|通知送信用メールアドレス/,
    })
    await expect(organizationSettingRows).toHaveCount(8)
    await expect(organizationSettingRows.getByText('固定設定')).toHaveCount(8)

    const nameRow = organizationSettingRows.filter({ hasText: '取次者 氏名' })
    await expect(nameRow).toBeVisible()

    await nameRow.dblclick()
    await expect(nameRow.locator('input')).toHaveCount(0)

    await nameRow.focus()
    await page.keyboard.press('Enter')
    await expect(nameRow.locator('input')).toHaveCount(0)
  })

  test('value alternatives expand and can be adopted', async ({ page }) => {
    const salaryRow = page.locator('[data-field-row]').filter({ hasText: '月額給与' })
    await expect(salaryRow).toBeVisible()

    await salaryRow.getByRole('button', { name: '別候補1' }).click()

    await expect(page.getByText('現在の値')).toBeVisible()
    await expect(page.getByText('別候補 1')).toBeVisible()
    await expect(page.getByText('resume.pdf / p.2')).toBeVisible()
    await expect(page.getByText('希望給与 280000')).toBeVisible()

    await page.getByRole('button', { name: '採用' }).click()

    await expect(salaryRow.getByText('280000')).toBeVisible()
    await expect(page.getByRole('button', { name: '採用中' })).toBeVisible()
  })
})

test.describe('Demo mode navigation', () => {
  test('case list → click case → review page preserves demo mode', async ({ page }) => {
    await page.goto('/?demo=true')
    await expect(page.getByRole('heading', { name: '案件一覧' })).toBeVisible()

    // Click the demo case card outside the copyable case_id control
    await page.getByText('NGUYEN VAN DEMO / デモテクノロジー株式会社').click()

    // Should navigate to review page with demo=true
    await expect(page).toHaveURL(/\/cases\/demo-gijinkoku-001\/review\?demo=true/)
    await expect(page.getByText('demo-gijinkoku-001').first()).toBeVisible()
    await expect(page.locator('[data-field-row]').first()).toBeVisible()

    // Go back and verify demo mode is maintained
    await page.goBack()
    await expect(page).toHaveURL(/\?demo=true/)
    await expect(page.getByRole('heading', { name: '案件一覧' })).toBeVisible()
    await expect(page.getByText('demo-gijinkoku-001')).toBeVisible()
  })
})

test.describe('UploadPage demo mode', () => {
  test('shows DropZone with Japanese text', async ({ page }) => {
    await page.goto('/cases/demo/upload?demo=true')
    await expect(page.getByText('ここにファイルをドラッグ＆ドロップ')).toBeVisible()
    await expect(page.getByText('ファイルを選択')).toBeVisible()
  })
})

test.describe('UploadPage backend selection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/cases/demo/upload?demo=true')
  })

  test('shows extraction engine and pattern selectors', async ({ page }) => {
    await expect(page.getByText('抽出エンジン')).toBeVisible()
    await expect(page.getByText('抽出方式')).toBeVisible()
  })

  test('default backend is Gemini', async ({ page }) => {
    const backendSelect = page.locator('select').first()
    await expect(backendSelect).toHaveValue('gemini')
  })

  test('default pattern is auto', async ({ page }) => {
    const patternSelect = page.locator('select').nth(1)
    await expect(patternSelect).toHaveValue('auto')
  })

  test('can switch backend to Codex', async ({ page }) => {
    const backendSelect = page.locator('select').first()
    await backendSelect.selectOption('codex')
    await expect(backendSelect).toHaveValue('codex')
  })

  test('can switch pattern to text_only', async ({ page }) => {
    const patternSelect = page.locator('select').nth(1)
    await patternSelect.selectOption('text_only')
    await expect(patternSelect).toHaveValue('text_only')
  })
})

test.describe('Navigation', () => {
  test('redirects unknown paths to /', async ({ page }) => {
    await page.goto('/nonexistent-path?demo=true')
    await page.waitForURL(/^http:\/\/(localhost|127\.0\.0\.1):\d+\/(\?.*)?$/)
    await expect(page.getByRole('heading', { name: '案件一覧' })).toBeVisible()
  })
})
