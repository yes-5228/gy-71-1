<template>
  <div v-if="visible" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <h3>续租办理</h3>
      <p class="modal-subtitle">原合同：{{ contract?.contract_no }} / {{ contract?.tenant_name }}</p>

      <div v-if="showWorkstationWarning" class="warning-box">
        <strong>⚠ 工位状态异常</strong>
        <p>该工位当前状态为「{{ workstationStatusText }}」，不是正常出租状态。</p>
        <p>续租将自动把工位恢复为「已租」状态，是否继续？</p>
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
        <button type="button" class="primary-button" @click="handleSubmit" :disabled="submitting">
          {{ submitting ? '提交中...' : '确认续租' }}
        </button>
      </div>
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
const confirmedWorkstationWarning = ref(false)

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
  confirmedWorkstationWarning.value = false
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
  showWorkstationWarning.value = status && status !== 'leased'
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

  if (showWorkstationWarning.value && !confirmedWorkstationWarning.value) {
    const ok = window.confirm(
      `该工位当前状态为「${workstationStatusText.value}」，不是正常出租状态。\n续租后工位将被自动恢复为「已租」，是否继续？`
    )
    if (!ok) return
    confirmedWorkstationWarning.value = true
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
</style>
