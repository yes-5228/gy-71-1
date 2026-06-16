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

    <RenewModal
      :visible="showRenewModal"
      :contract="renewingContract"
      @close="closeRenewModal"
      @success="onRenewSuccess"
    />
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { fetchExpiringContracts, fetchOverduePayments } from '../api/reminders'
import SectionToolbar from '../components/SectionToolbar.vue'
import RenewModal from '../components/RenewModal.vue'
import { currency } from '../utils/formatters'

const contracts = ref([])
const payments = ref([])
const error = ref('')

const showRenewModal = ref(false)
const renewingContract = ref(null)

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

function openRenewModal(contract) {
  renewingContract.value = contract
  showRenewModal.value = true
}

function closeRenewModal() {
  showRenewModal.value = false
  renewingContract.value = null
}

async function onRenewSuccess() {
  closeRenewModal()
  await load()
}

onMounted(load)
</script>

<style scoped>
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

.ghost-button {
  background: #ffffff;
  border: 1px solid #cfd8e3;
  border-radius: 6px;
  color: #17202a;
  min-height: 38px;
  padding: 8px 16px;
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
