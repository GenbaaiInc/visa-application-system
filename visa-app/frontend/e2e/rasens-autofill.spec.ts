import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const contentScriptPath = fileURLToPath(new URL('../../../rasens-autofill/extension/content.js', import.meta.url))
const popupScriptPath = fileURLToPath(new URL('../../../rasens-autofill/extension/popup.js', import.meta.url))
const popupHtmlPath = fileURLToPath(new URL('../../../rasens-autofill/extension/popup.html', import.meta.url))

type FormProfile = { application_type?: string; target_status?: string } | null
type FillRow = {
  label: string
  field_id: string
  field_name: string
  input_type: string
  fill_value: string
}

type AutofillWindow = Window & {
  __visaAutofillContentHandler: (
    message: { type: string; rows: FillRow[]; formProfile: FormProfile },
    sender: null,
    respond: (response: { message: string }) => void,
  ) => boolean
}

const sswProfile = {
  application_type: 'certificate_of_eligibility',
  target_status: 'specified_skilled_worker',
}

const sexRow: FillRow = {
  label: '性別',
  field_id: 'sex_1',
  field_name: 'item[8].selectData',
  input_type: 'radio',
  fill_value: '女 Female',
}

function formHtml(options: {
  applicationTitle?: string
  currentStatus?: string
  targetStatus?: string
  hiddenChoiceRow?: boolean
  disabledChoices?: boolean
} = {}) {
  const {
    applicationTitle = '在留資格認定証明書交付申請',
    currentStatus,
    targetStatus = '特定技能 Specified Skilled Worker',
    hiddenChoiceRow = false,
    disabledChoices = false,
  } = options
  const statusField = (title: string, value: string) =>
    `<dl class="c-input"><dt class="c-input__title">${title}</dt><dd>${value}</dd></dl>`

  return `
    <style>.radio-input { display: none; } .radio-outline { display: inline-block; padding: 4px; }</style>
    <h1>${applicationTitle}</h1>
    <form id="frm">
      ${currentStatus ? statusField('現在の在留資格', currentStatus) : ''}
      ${targetStatus ? statusField('希望する在留資格', targetStatus) : ''}
      <select name="item[0].selectData"><option>選択してください</option></select>
      <dl class="c-input" ${hiddenChoiceRow ? 'style="display: none"' : ''}>
        <dt class="c-input__title">性別</dt>
        <dd>
          <label class="radio-outline"><input class="radio-input" id="sex_1" name="item[8].selectData" type="radio" value="1" ${disabledChoices ? 'disabled' : ''}>男 Male</label>
          <label class="radio-outline"><input class="radio-input" id="sex_2" name="item[8].selectData" type="radio" value="2" ${disabledChoices ? 'disabled' : ''}>女 Female</label>
        </dd>
      </dl>
    </form>
  `
}

async function loadAutofill(page: Page, html: string) {
  await page.setContent(html)
  await page.addScriptTag({ content: 'window.chrome = { runtime: { onMessage: { addListener() {}, removeListener() {} } } }' })
  await page.addScriptTag({ path: contentScriptPath })
}

async function fill(page: Page, rows: FillRow[], formProfile: FormProfile) {
  return page.evaluate(({ rows, formProfile }) => new Promise<string>((resolve) => {
    (window as AutofillWindow).__visaAutofillContentHandler(
      { type: 'VISA_AUTOFILL_FILL', rows, formProfile },
      null,
      (response) => resolve(response.message),
    )
  }), { rows, formProfile })
}

test.use({ screenshot: 'off' })

test.describe('RASENS autofill guard and visibility', () => {
  test('fills a radio whose native input is hidden inside a visible label', async ({ page }) => {
    await loadAutofill(page, formHtml())
    expect(await fill(page, [sexRow], sswProfile)).toContain('1件入力')
    await expect(page.locator('#sex_2')).toBeChecked()
  })

  for (const [condition, html] of [
    ['hidden row', formHtml({ hiddenChoiceRow: true })],
    ['disabled radio', formHtml({ disabledChoices: true })],
  ] as const) {
    test(`does not fill a ${condition}`, async ({ page }) => {
      await loadAutofill(page, html)
      expect(await fill(page, [sexRow], sswProfile)).toContain('0件入力、1件スキップ')
      await expect(page.locator('#sex_2')).not.toBeChecked()
    })
  }

  for (const [mismatch, row] of [
    ['field ID', { ...sexRow, field_id: 'old_sex_1' }],
    ['field name', { ...sexRow, field_name: 'item[99].selectData' }],
    ['input type', { ...sexRow, input_type: 'text' }],
  ] as const) {
    test(`does not fill SSW row with mismatched ${mismatch}`, async ({ page }) => {
      await loadAutofill(page, formHtml())
      expect(await fill(page, [row], sswProfile)).toContain('1件未検出')
      await expect(page.locator('#sex_2')).not.toBeChecked()
    })
  }

  for (const [name, formProfile] of [
    ['missing profile', null],
    ['empty profile', {}],
    ['partial profile', { application_type: 'certificate_of_eligibility' }],
  ] as const) {
    test(`rejects ${name} before entering any data`, async ({ page }) => {
      await loadAutofill(page, formHtml())
      expect(await fill(page, [sexRow], formProfile)).toContain('再読み込み')
      await expect(page.locator('#sex_2')).not.toBeChecked()
    })
  }

  test('fills an ID-only text control that has no name in RASENS', async ({ page }) => {
    await loadAutofill(page, formHtml())
    await page.evaluate(() => {
      const input = document.createElement('input')
      input.id = 'textData1_123'
      input.type = 'text'
      document.querySelector('#frm')?.append(input)
    })
    expect(await fill(page, [{
      label: '生年月日',
      field_id: 'textData1_123',
      field_name: '',
      input_type: 'text',
      fill_value: '19900101',
    }], sswProfile)).toContain('1件入力')
    await expect(page.locator('#textData1_123')).toHaveValue('19900101')
  })

  test('uses desired status, not current status, for a change application', async ({ page }) => {
    await loadAutofill(page, formHtml({
      applicationTitle: '在留資格変更許可申請',
      currentStatus: '技術・人文知識・国際業務',
    }))
    expect(await fill(page, [sexRow], {
      application_type: 'change_of_status',
      target_status: 'specified_skilled_worker',
    })).toContain('1件入力')
    await expect(page.locator('#sex_2')).toBeChecked()
  })

  test('uses current status fixed display for a renewal application', async ({ page }) => {
    await loadAutofill(page, formHtml({
      applicationTitle: '在留期間更新許可申請',
      currentStatus: '特定技能 Specified Skilled Worker',
      targetStatus: '',
    }))
    expect(await fill(page, [sexRow], {
      application_type: 'extension_of_stay',
      target_status: 'specified_skilled_worker',
    })).toContain('1件入力')
    await expect(page.locator('#sex_2')).toBeChecked()
  })

  test('replaces an old page handler before rejecting rows without a profile', async ({ page }) => {
    await page.setContent(formHtml())
    await page.addScriptTag({ content: `
      window.__oldHandlerCalled = false;
      window.__oldHandler = (_message, _sender, respond) => {
        window.__oldHandlerCalled = true;
        respond({ message: 'old handler filled' });
        return true;
      };
      window.__listeners = [window.__oldHandler];
      window.__visaAutofillContentHandler = window.__oldHandler;
      window.chrome = { runtime: { onMessage: {
        addListener(handler) { window.__listeners.push(handler); },
        removeListener(handler) {
          window.__listeners = window.__listeners.filter((item) => item !== handler);
        },
      } } };
    ` })
    await page.addScriptTag({ path: contentScriptPath })

    const state = await page.evaluate(() => {
      const view = window as AutofillWindow & {
        __listeners: AutofillWindow['__visaAutofillContentHandler'][]
        __oldHandler: AutofillWindow['__visaAutofillContentHandler']
        __oldHandlerCalled: boolean
      }
      return {
        listenerCount: view.__listeners.length,
        oldRemoved: !view.__listeners.includes(view.__oldHandler),
        newInstalled: view.__listeners[0] === view.__visaAutofillContentHandler,
        oldHandlerCalled: view.__oldHandlerCalled,
      }
    })
    expect(state).toEqual({ listenerCount: 1, oldRemoved: true, newInstalled: true, oldHandlerCalled: false })

    const response = await page.evaluate((row) => new Promise<string>((resolve) => {
      const view = window as AutofillWindow & {
        __listeners: AutofillWindow['__visaAutofillContentHandler'][]
      }
      view.__listeners[0]({ type: 'VISA_AUTOFILL_FILL', rows: [row], formProfile: null }, null, (result) => {
        resolve(result.message)
      })
    }), sexRow)
    expect(response).toContain('再読み込み')
    await expect(page.locator('#sex_2')).not.toBeChecked()
    expect(await page.evaluate(() => (window as Window & { __oldHandlerCalled: boolean }).__oldHandlerCalled)).toBe(false)
  })

  test('injects the current content script before sending saved rows', async ({ page }) => {
    const popupHtml = readFileSync(popupHtmlPath, 'utf8').replace(/<script[^>]*><\/script>/g, '')
    await page.setContent(popupHtml)
    await page.addScriptTag({ content: `
      window.__events = [];
      window.chrome = {
        storage: { local: {
          async get() { return {
            visaRows: [${JSON.stringify(sexRow)}], visaFillable: true,
            visaFormProfile: null, visaPendingManualFields: [],
          }; },
          async set() {}, async remove() {},
        } },
        tabs: {
          async query() { return [{ id: 7, url: 'https://www.rasens-immi.moj.go.jp/rasens-u/offer/offerRSS_gotoOffer' }]; },
          async sendMessage() {
            window.__events.push('send');
            return { message: '入力データの対象手続き情報がありません。再読み込みしてください' };
          },
        },
        scripting: { async executeScript() { window.__events.push('inject'); } },
      };
      window.apiClient = { async getAuthState() { return { email: 'test@example.com' }; },
        async listCases() { return []; } };
    ` })
    await page.addScriptTag({ path: popupScriptPath })
    await expect(page.locator('#fill')).toBeEnabled()
    await page.locator('#fill').click()
    await expect(page.locator('#status')).toContainText('再読み込みしてください')
    expect(await page.evaluate(() => (window as Window & { __events: string[] }).__events)).toEqual(['inject', 'send'])
  })
})

test('popup filters cases by status and shows procedure and status before loading', async ({ page }) => {
  const popupHtml = readFileSync(popupHtmlPath, 'utf8').replace(/<script[^>]*><\/script>/g, '')
  await page.setContent(popupHtml)
  await page.addScriptTag({ content: `
    window.__cases = [
      { case_id: 'coe-gijinkoku', display_name: '佐藤さん', application_type: 'certificate_of_eligibility', target_status: 'engineer_humanities_international' },
      { case_id: 'renewal-ssw1', display_name: '山田さん', application_type: 'extension_of_stay', target_status: 'specified_skilled_worker', target_status_variant: 'ssw_1' },
      { case_id: 'change-ssw2', display_name: '田中さん', application_type: 'change_of_status', target_status: 'specified_skilled_worker', target_status_variant: 'ssw_2' },
    ];
    window.__stored = {};
    window.chrome = { storage: { local: {
      async get(keys) { return Object.fromEntries(keys.map((key) => [key, window.__stored[key]])); },
      async set(values) { Object.assign(window.__stored, values); },
      async remove() {},
    } } };
    window.apiClient = {
      async getAuthState() { return { email: 'test@example.com' }; },
      async listCases() { return window.__cases; },
      async getApplicationData() { throw new Error('filter must not load a case'); },
    };
  ` })
  await page.addScriptTag({ path: popupScriptPath })

  const caseSelect = page.locator('#caseSelect')
  await expect(caseSelect.locator('option')).toHaveCount(4)
  await expect(caseSelect.locator('option[value="coe-gijinkoku"]')).toContainText('[認定・技人国] 佐藤さん')
  await expect(caseSelect.locator('option[value="renewal-ssw1"]')).toContainText('[更新・特定技能1号] 山田さん')
  await expect(caseSelect.locator('option[value="change-ssw2"]')).toContainText('[変更・特定技能2号] 田中さん')

  await page.locator('#statusFilter').selectOption('specified_skilled_worker')
  await expect(caseSelect.locator('option')).toHaveCount(3)
  await expect(caseSelect.locator('option[value="coe-gijinkoku"]')).toHaveCount(0)
  await expect(page.locator('#caseListStatus')).toHaveText('2件を表示（全3件）')
  await caseSelect.selectOption('renewal-ssw1')
  await expect.poll(() => page.evaluate(() => (window as Window & { __stored: Record<string, string> }).__stored.visaSelectedCaseId)).toBe('renewal-ssw1')

  await page.locator('#statusFilter').selectOption('engineer_humanities_international')
  await expect(caseSelect).toHaveValue('')
  await expect(caseSelect.locator('option[value="coe-gijinkoku"]')).toHaveCount(1)
  await expect(caseSelect.locator('option[value="renewal-ssw1"]')).toHaveCount(0)
  expect(await page.evaluate(() => (window as Window & { __cases: Array<{ target_status: string }> }).__cases.map((item) => item.target_status)))
    .toEqual(['engineer_humanities_international', 'specified_skilled_worker', 'specified_skilled_worker'])
})
