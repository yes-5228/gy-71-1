<template>
  <section class="panel">
    <SectionToolbar eyebrow="Reminders" title="到期与逾期提醒">
      <button type="button" class="ghost-button" @click="load">刷新</button>
    </SectionToolbar>

    <p v-if="error" class="error">{{ error }}</p>
    <div class="split-grid">
      <div>
        <h3>30天内到期合同</h3>
        <div class="list">
          <article v-for="contract in contracts" :key="contract.id" class="list-item">
            <div class="list-item-header">
              <strong>{{ contract.tenant_name }}</strong>
              <button type="button" class="small-button renew-btn" @click="openRenewModal(contract)">续租办理</button>
            </div>
            <span>{{ contract.contract_no }} / {{ contract.workstation?.code || '-' }}</span>
            <span>到期日：{{ contract.end_date }}</span>
          </article>
          <p v-if="!contracts.length" class="empty">暂无即将到期合同</p>
        </div>
      </div>
      <div>
        <h3>逾期未收账单</h3>
        <div class="list">
          <article v-for="payment in payments" :key="payment.id" class="list-item danger-line">
            <strong>{{ payment.tenant_name }}</strong>
            <span>{{ payment.contract_no }} / {{ payment.period }}</span>
            <span>{{ currency(payment.amount) }}，应收日 {{ payment.due_date }}</span>
          </article>
          <p v-if="!payments.length" class="empty">暂无逾期账单</p>
        </div>
      </div>
    </div>

    <div v-if="showRenewModal" class="modal-overlay" @click.self="closeRenewModal">
      <div class="modal-content">
        <h3>续租办理</h3>
        <p class="modal-subtitle">原合同：{{ renewingContract?.contract_no }} / {{ renewingContract?.tenant_name }}</p>

        <div class="form-grid">
          <div>
            <label>租期方案</label>
            <select v-model="renewForm.termOption" @change="applyTermOption">
              <option value="custom">自定义</option>
              <option value="3m">3 个月</option>
              <option value="6m">6 个月</option>
              <option value="12m">12 个月（推荐）</option>
            </select>
          </div>
          <div>
            <label>开始日期</label>
            <input v-model="renewForm.start_date" type="date" />
          </div>
          <div>
            <label>结束日期</label>
            <input v-model="renewForm.end_date" type="date" />
          </div>
          <div>
            <label>月租金方案</label>
            <select v-model="renewForm.rentOption" @change="applyRentOption">
              <option value="custom">自定义</option>
              <option value="same">沿用原租金</option>
              <option value="increase5">上调 5%</option>
              <option value="increase10">上调 10%</option>
            </select>
          </div>
          <div>
            <label>月租金（元）</label>
            <input v-model.number="renewForm.monthly_rent" type="number" min="0" />
          </div>
          <div>
            <label>押金（元）</label>
            <input v-model.number="renewForm.deposit" type="number" min="0" />
          </div>
          <div>
            <label>租户名称</label>
            <input v-model="renewForm.tenant_name" />
          </div>
          <div>
            <label>联系人/电话</label>
            <input v-model="renewForm.tenant_contact" />
          </div>
        </div>

        <div class="renew-summary">
          <h4>续租信息确认</h4>
          <p>新租期：{{ renewForm.start_date }} 至 {{ renewForm.end_date }}</p>
          <p>月租金：{{ currency(renewForm.monthly_rent) }}</p>
          <p>押金：{{ currency(renewForm.deposit) }}</p>
        </div>

        <p v-if="renewError" class="error">{{ renewError }}</p>

        <div class="modal-actions">
          <button type="button" class="ghost-button" @click="closeRenewModal">取消</button>
          <button type="button" class="primary-button" @click="submitRenewal">确认续租</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { fetchExpiringContracts, fetchOverduePayments } from '../api/reminders'
import { renewContract } from '../api/contracts'
import SectionToolbar from '../components/SectionToolbar.vue'
import { currency } from '../utils/formatters'

const contracts = ref([])
const payments = ref([])
const error = ref('')

const showRenewModal = ref(false)
const renewingContract = ref(null)
const renewError = ref('')
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

async function load() {
  error.value = ''
  try {
    const [expiring, overdue] = await Promise.all([fetchExpiringContracts(30), fetchOverduePayments()])
    contracts.value = expiring
    payments.value = overdue
  } catch (err) {
    error.value = err.message
  }
}

function addMonths(dateStr, months) {
  const d = new Date(dateStr)
  d.setMonth(d.getMonth() + months)
  return d.toISOString().slice(0, 10)
}

function openRenewModal(contract) {
  renewingContract.value = contract
  renewError.value = ''

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

  showRenewModal.value = true
}

function closeRenewModal() {
  showRenewModal.value = false
  renewingContract.value = null
  renewError.value = ''
}

function applyTermOption() {
  if (!renewingContract.value) return
  const start = renewForm.start_date || renewingContract.value.end_date

  const monthsMap = { '3m': 3, '6m': 6, '12m': 12 }
  if (renewForm.termOption in monthsMap) {
    renewForm.end_date = addMonths(start, monthsMap[renewForm.termOption])
  }
}

function applyRentOption() {
  if (!renewingContract.value) return
  const originalRent = Number(renewingContract.value.monthly_rent)

  if (renewForm.rentOption === 'same') {
    renewForm.monthly_rent = originalRent
  } else if (renewForm.rentOption === 'increase5') {
    renewForm.monthly_rent = Math.round(originalRent * 1.05)
  } else if (renewForm.rentOption === 'increase10') {
    renewForm.monthly_rent = Math.round(originalRent * 1.10)
  }
}

async function submitRenewal() {
  if (!renewingContract.value) return
  renewError.value = ''

  try {
    await renewContract(renewingContract.value.id, {
      start_date: renewForm.start_date,
      end_date: renewForm.end_date,
      monthly_rent: renewForm.monthly_rent,
      deposit: renewForm.deposit,
      tenant_name: renewForm.tenant_name,
      tenant_contact: renewForm.tenant_contact
    })
    closeRenewModal()
    await load()
  } catch (err) {
    renewError.value = err.message
  }
}

onMounted(load)
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

.form-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  margin-bottom: 18px;
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

.ghost-button {
  background: #ffffff;
  border: 1px solid #cfd8e3;
  border-radius: 6px;
  color: #17202a;
  min-height: 38px;
  padding: 8px 16px;
}

.small-button {
  background: #ffffff;
  border: 1px solid #cfd8e3;
  border-radius: 6px;
  color: #17202a;
  padding: 4px 10px;
  font-size: 13px;
  min-height: 28px;
}

.renew-btn {
  background: #1d5f8f;
  border-color: #1d5f8f;
  color: #ffffff;
  white-space: nowrap;
}

.renew-btn:hover {
  background: #174d75;
}

.list-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.empty {
  color: #8696a7;
  text-align: center;
  padding: 24px;
}
</style>
