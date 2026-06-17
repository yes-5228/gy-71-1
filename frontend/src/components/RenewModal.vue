<template>
  <div v-if="visible" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <template v-if="!showSuccess">
        <h3>续租办理</h3>
        <p class="modal-subtitle">原合同：{{ contract?.contract_no }} / {{ contract?.tenant_name }}</p>

        <div v-if="showWorkstationWarning" class="warning-box">
          <strong>⚠ 工位状态异常</strong>
          <p>该工位当前状态为「{{ workstationStatusText }}」，不是正常出租状态。</p>
          <p>续租后工位将被自动恢复为「已租」状态，请确认已了解风险。</p>
        </div>

        <div class="form-grid">
          <div>
            <label>租期方案</label>
            <select v-model="renewForm.termOption" @change="applyTermOption" :disabled="submitting">
              <option value="custom">自定义</option>
              <option value="3m">3 个月</option>
              <option value="6m">6 个月</option>
              <option value="12m">12 个月（推荐）</option>
            </select>
          </div>
          <div>
            <label>开始日期</label>
            <input v-model="renewForm.start_date" type="date" :disabled="submitting" />
          </div>
          <div>
            <label>结束日期</label>
            <input v-model="renewForm.end_date" type="date" :disabled="submitting" />
          </div>
          <div>
            <label>月租金方案</label>
            <select v-model="renewForm.rentOption" @change="applyRentOption" :disabled="submitting">
              <option value="custom">自定义</option>
              <option value="same">沿用原租金</option>
              <option value="increase5">上调 5%</option>
              <option value="increase10">上调 10%</option>
            </select>
          </div>
          <div>
            <label>月租金（元）</label>
            <input v-model.number="renewForm.monthly_rent" type="number" min="0" :disabled="submitting" />
          </div>
          <div>
            <label>押金（元）</label>
            <input v-model.number="renewForm.deposit" type="number" min="0" :disabled="submitting" />
          </div>
          <div>
            <label>租户名称</label>
            <input v-model="renewForm.tenant_name" :disabled="submitting" />
          </div>
          <div>
            <label>联系人/电话</label>
            <input v-model="renewForm.tenant_contact" :disabled="submitting" />
          </div>
        </div>

        <div class="renew-summary">
          <h4>续租信息确认</h4>
          <p>新租期：{{ renewForm.start_date }} 至 {{ renewForm.end_date }}</p>
          <p>月租金：{{ currency(renewForm.monthly_rent) }}</p>
          <p>押金：{{ currency(renewForm.deposit) }}</p>
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <div class="modal-actions">
          <button type="button" class="ghost-button" @click="handleClose" :disabled="submitting">取消</button>
          <button
            type="button"
            class="primary-button"
            :class="{ 'danger-confirm': needsRiskConfirmation }"
            @click="handleSubmit"
            :disabled="submitting"
          >
            <template v-if="submitting">提交中...</template>
            <template v-else-if="needsRiskConfirmation">我已了解风险，确认续租</template>
            <template v-else>确认续租</template>
          </button>
        </div>
      </template>

      <template v-else>
        <div class="success-icon">✓</div>
        <h3 class="success-title">续租已完成</h3>
        <p class="success-desc">原合同已标记为「已续租」，新合同已生效。</p>

        <div class="success-card">
          <h4>新合同信息</h4>
          <div class="info-row">
            <span class="info-label">合同编号</span>
            <span class="info-value">{{ newContract?.contract_no }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">租户名称</span>
            <span class="info-value">{{ newContract?.tenant_name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">工位编号</span>
            <span class="info-value">{{ newContract?.workstation?.code || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">新租期</span>
            <span class="info-value">{{ newContract?.start_date }} 至 {{ newContract?.end_date }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">月租金</span>
            <span class="info-value">{{ currency(newContract?.monthly_rent || 0) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">押金</span>
            <span class="info-value">{{ currency(newContract?.deposit || 0) }}</span>
          </div>
        </div>

        <div class="modal-actions">
          <button type="button" class="primary-button" @click="handleComplete">完成</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { renewContract } from '../api/contracts'
import { statusText, currency } from '../utils/formatters'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  contract: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'success'])

const error = ref('')
const submitting = ref(false)
const showWorkstationWarning = ref(false)
const needsRiskConfirmation = ref(false)
const showSuccess = ref(false)
const newContract = ref(null)

const renewForm = reactive({
  termOption: '12m',
  rentOption: 'same',
  start_date: '',
  end_date: '',
  monthly_rent: 0,
  deposit: 0,
  tenant_name: '',
  tenant_contact: ''
})

const workstationStatusText = computed(() => {
  if (props.contract?.workstation?.status) {
    return statusText(props.contract.workstation.status)
  }
  return ''
})

function addMonths(dateStr, months) {
  const d = new Date(dateStr)
  d.setMonth(d.getMonth() + months)
  return d.toISOString().slice(0, 10)
}

function resetForm() {
  error.value = ''
  submitting.value = false
  showWorkstationWarning.value = false
  needsRiskConfirmation.value = false
  showSuccess.value = false
  newContract.value = null
}

function initForm(contract) {
  if (!contract) return
  const defaultStart = contract.end_date
  Object.assign(renewForm, {
    termOption: '12m',
    rentOption: 'same',
    start_date: defaultStart,
    end_date: addMonths(defaultStart, 12),
    monthly_rent: Number(contract.monthly_rent),
    deposit: Number(contract.deposit),
    tenant_name: contract.tenant_name,
    tenant_contact: contract.tenant_contact || ''
  })
}

function checkWorkstationStatus() {
  const status = props.contract?.workstation?.status
  const hasWarning = status && status !== 'leased'
  showWorkstationWarning.value = hasWarning
  needsRiskConfirmation.value = hasWarning
}

watch(
  () => props.visible,
  (val) => {
    if (val && props.contract) {
      resetForm()
      initForm(props.contract)
      checkWorkstationStatus()
    }
  }
)

watch(
  () => props.contract,
  () => {
    if (props.visible && props.contract) {
      resetForm()
      initForm(props.contract)
      checkWorkstationStatus()
    }
  }
)

function applyTermOption() {
  if (!props.contract) return
  const start = renewForm.start_date || props.contract.end_date
  const monthsMap = { '3m': 3, '6m': 6, '12m': 12 }
  if (renewForm.termOption in monthsMap) {
    renewForm.end_date = addMonths(start, monthsMap[renewForm.termOption])
  }
}

function applyRentOption() {
  if (!props.contract) return
  const originalRent = Number(props.contract.monthly_rent)
  if (renewForm.rentOption === 'same') {
    renewForm.monthly_rent = originalRent
  } else if (renewForm.rentOption === 'increase5') {
    renewForm.monthly_rent = Math.round(originalRent * 1.05)
  } else if (renewForm.rentOption === 'increase10') {
    renewForm.monthly_rent = Math.round(originalRent * 1.10)
  }
}

async function handleSubmit() {
  if (!props.contract || submitting.value) return

  if (needsRiskConfirmation.value) {
    needsRiskConfirmation.value = false
    return
  }

  error.value = ''
  submitting.value = true

  try {
    const result = await renewContract(props.contract.id, {
      start_date: renewForm.start_date,
      end_date: renewForm.end_date,
      monthly_rent: renewForm.monthly_rent,
      deposit: renewForm.deposit,
      tenant_name: renewForm.tenant_name,
      tenant_contact: renewForm.tenant_contact
    })
    newContract.value = result
    showSuccess.value = true
    emit('success', result)
  } catch (err) {
    error.value = err.message
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  if (submitting.value) return
  emit('close')
}

function handleComplete() {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: #ffffff;
  border-radius: 12px;
  max-width: 640px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  padding: 24px;
}

.modal-content h3 {
  margin: 0 0 4px;
  font-size: 20px;
}

.modal-subtitle {
  color: #607080;
  margin: 0 0 20px;
  font-size: 14px;
}

.modal-content label {
  display: block;
  font-size: 13px;
  color: #52616f;
  margin-bottom: 4px;
}

.modal-content select,
.modal-content input {
  width: 100%;
  border: 1px solid #c7d1dc;
  border-radius: 6px;
  min-height: 40px;
  padding: 8px 10px;
}

.modal-content select:disabled,
.modal-content input:disabled {
  background: #f4f6f8;
  color: #8696a7;
  cursor: not-allowed;
}

.form-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  margin-bottom: 18px;
}

.warning-box {
  background: #fff4d6;
  border: 1px solid #f0b429;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 16px;
  color: #7a5200;
}

.warning-box strong {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
}

.warning-box p {
  margin: 4px 0;
  font-size: 13px;
}

.renew-summary {
  background: #f8fafc;
  border: 1px solid #d9e0e7;
  border-radius: 8px;
  padding: 14px 16px;
  margin: 16px 0;
}

.renew-summary h4 {
  margin: 0 0 8px;
  font-size: 15px;
}

.renew-summary p {
  margin: 4px 0;
  font-size: 14px;
  color: #334150;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.primary-button {
  background: #1d5f8f;
  border: 1px solid #1d5f8f;
  border-radius: 6px;
  color: #ffffff;
  min-height: 38px;
  padding: 8px 16px;
}

.primary-button:disabled {
  background: #8aa7c2;
  border-color: #8aa7c2;
  cursor: not-allowed;
}

.primary-button.danger-confirm {
  background: #d8345f;
  border-color: #d8345f;
}

.primary-button.danger-confirm:hover {
  background: #b4284e;
}

.ghost-button {
  background: #ffffff;
  border: 1px solid #cfd8e3;
  border-radius: 6px;
  color: #17202a;
  min-height: 38px;
  padding: 8px 16px;
}

.ghost-button:disabled {
  color: #8696a7;
  cursor: not-allowed;
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #10b981;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: bold;
  margin: 0 auto 16px;
}

.success-title {
  text-align: center;
  margin-bottom: 8px;
}

.success-desc {
  text-align: center;
  color: #607080;
  margin-bottom: 20px;
  font-size: 14px;
}

.success-card {
  background: #f8fafc;
  border: 1px solid #d9e0e7;
  border-radius: 8px;
  padding: 16px 20px;
}

.success-card h4 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #17202a;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
  border-bottom: 1px dashed #e0e6ec;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  color: #607080;
}

.info-value {
  color: #17202a;
  font-weight: 500;
}
</style>
