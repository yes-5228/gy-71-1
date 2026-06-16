<template>
  <section class="panel">
    <SectionToolbar eyebrow="Contracts" title="租赁合同管理">
      <select v-model="statusFilter" @change="loadContracts">
        <option value="">全部合同</option>
        <option value="active">履行中</option>
        <option value="renewed">已续租</option>
        <option value="terminated">已终止</option>
        <option value="expired">已到期</option>
      </select>
    </SectionToolbar>

    <form class="form-grid" @submit.prevent="submit">
      <input v-model="form.tenant_name" placeholder="租户名称" required />
      <input v-model="form.tenant_contact" placeholder="联系人/电话" />
      <select v-model.number="form.workstation_id" required>
        <option value="" disabled>选择可租工位</option>
        <option v-for="item in availableWorkstations" :key="item.id" :value="item.id">
          {{ item.code }} / {{ item.area }} / {{ currency(item.monthly_rent) }}
        </option>
      </select>
      <input v-model="form.start_date" type="date" required />
      <input v-model="form.end_date" type="date" required />
      <input v-model.number="form.monthly_rent" type="number" min="0" placeholder="月租金" required />
      <input v-model.number="form.deposit" type="number" min="0" placeholder="押金" />
      <button type="submit">签订合同</button>
    </form>

    <p v-if="error" class="error">{{ error }}</p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>合同号</th>
            <th>租户</th>
            <th>工位</th>
            <th>租期</th>
            <th>月租金</th>
            <th>押金</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="contract in contracts" :key="contract.id">
            <td>
              {{ contract.contract_no }}
              <small v-if="contract.renewal_count > 0">第 {{ contract.renewal_count }} 次续租</small>
            </td>
            <td>{{ contract.tenant_name }}<small>{{ contract.tenant_contact }}</small></td>
            <td>{{ contract.workstation?.code || '-' }}</td>
            <td>{{ contract.start_date }} 至 {{ contract.end_date }}</td>
            <td>{{ currency(contract.monthly_rent) }}</td>
            <td>{{ currency(contract.deposit) }}</td>
            <td><StatusBadge :value="contract.status" /></td>
            <td>
              <button v-if="contract.status === 'active'" class="small-button" type="button" @click="openRenewModal(contract)">续租</button>
              <button class="small-button ghost-button" type="button" @click="openHistoryModal(contract)">历史</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showHistoryModal" class="modal-overlay" @click.self="closeHistoryModal">
      <div class="modal-content">
        <h3>续租历史</h3>
        <p class="modal-subtitle">合同：{{ historyContract?.contract_no }}</p>

        <div v-if="historyLoading" class="empty">加载中...</div>
        <div v-else-if="!renewalHistory.length" class="empty">暂无续租历史</div>
        <div v-else class="history-timeline">
          <div v-for="(item, index) in renewalHistory" :key="item.id" class="history-item">
            <div class="history-dot" :class="{ active: item.status === 'active' }"></div>
            <div class="history-content">
              <strong>{{ item.contract_no }}</strong>
              <span class="history-tenant">{{ item.tenant_name }}</span>
              <small>{{ item.start_date }} 至 {{ item.end_date }}</small>
              <span>{{ currency(item.monthly_rent) }} / 月</span>
              <StatusBadge :value="item.status" />
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button type="button" class="ghost-button" @click="closeHistoryModal">关闭</button>
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
import { onMounted, reactive, ref, watch } from 'vue'
import { createContract, fetchContracts, fetchRenewalHistory } from '../api/contracts'
import { fetchWorkstations } from '../api/workstations'
import SectionToolbar from '../components/SectionToolbar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import RenewModal from '../components/RenewModal.vue'
import { currency, todayISO } from '../utils/formatters'

const contracts = ref([])
const availableWorkstations = ref([])
const statusFilter = ref('')
const error = ref('')
const form = reactive({
  tenant_name: '',
  tenant_contact: '',
  workstation_id: '',
  start_date: todayISO(),
  end_date: '',
  monthly_rent: 0,
  deposit: 0
})

const showRenewModal = ref(false)
const renewingContract = ref(null)

const showHistoryModal = ref(false)
const historyContract = ref(null)
const renewalHistory = ref([])
const historyLoading = ref(false)

watch(
  () => form.workstation_id,
  (id) => {
    const item = availableWorkstations.value.find((workstation) => workstation.id === Number(id))
    if (item) {
      form.monthly_rent = Number(item.monthly_rent)
      form.deposit = Number(item.monthly_rent) * 2
    }
  }
)

async function loadContracts() {
  error.value = ''
  try {
    contracts.value = await fetchContracts(statusFilter.value)
  } catch (err) {
    error.value = err.message
  }
}

async function loadWorkstations() {
  availableWorkstations.value = await fetchWorkstations('available')
}

async function load() {
  try {
    await Promise.all([loadContracts(), loadWorkstations()])
  } catch (err) {
    error.value = err.message
  }
}

async function submit() {
  error.value = ''
  try {
    await createContract({ ...form, workstation_id: Number(form.workstation_id) })
    Object.assign(form, {
      tenant_name: '',
      tenant_contact: '',
      workstation_id: '',
      start_date: todayISO(),
      end_date: '',
      monthly_rent: 0,
      deposit: 0
    })
    await load()
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

async function openHistoryModal(contract) {
  historyContract.value = contract
  renewalHistory.value = []
  historyLoading.value = true
  showHistoryModal.value = true

  try {
    renewalHistory.value = await fetchRenewalHistory(contract.id)
  } catch (err) {
    console.error(err)
  } finally {
    historyLoading.value = false
  }
}

function closeHistoryModal() {
  showHistoryModal.value = false
  historyContract.value = null
  renewalHistory.value = []
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

.small-button + .small-button {
  margin-left: 6px;
}

.ghost-button {
  background: #ffffff;
  border: 1px solid #cfd8e3;
  border-radius: 6px;
  color: #17202a;
  min-height: 38px;
  padding: 8px 16px;
}

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

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.history-timeline {
  position: relative;
  padding-left: 24px;
}

.history-item {
  position: relative;
  padding-bottom: 16px;
}

.history-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: -18px;
  top: 8px;
  bottom: -8px;
  width: 2px;
  background: #d9e0e7;
}

.history-dot {
  position: absolute;
  left: -22px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #cfd8e3;
  border: 2px solid #ffffff;
  box-shadow: 0 0 0 1px #cfd8e3;
}

.history-dot.active {
  background: #1d5f8f;
  box-shadow: 0 0 0 2px #1d5f8f33;
}

.history-content {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 12px;
  align-items: center;
}

.history-content strong {
  font-size: 14px;
}

.history-tenant {
  grid-column: 1;
  font-size: 13px;
  color: #334150;
  font-weight: 500;
}

.history-content small {
  grid-column: 1;
  color: #607080;
  font-size: 12px;
}

.history-content span {
  grid-column: 1;
  color: #52616f;
  font-size: 13px;
}

.empty {
  color: #8696a7;
  text-align: center;
  padding: 24px;
}

td small {
  color: #8696a7;
  font-size: 12px;
  display: block;
  margin-top: 3px;
}
</style>
