<template>
  <main v-if="!token" class="login-page">
    <section class="login-card">
      <div>
        <p class="eyebrow">青玄 Console</p>
        <h1>青玄商业管理后台</h1>
        <p class="muted">用户、积分、客服和产品规则统一管理。</p>
      </div>
      <el-input v-model="loginForm.username" placeholder="管理员账号" size="large" />
      <el-input v-model="loginForm.password" placeholder="管理员密码" size="large" show-password @keyup.enter="login" />
      <el-button type="primary" size="large" @click="login">登录后台</el-button>
      <p class="hint">默认账号：admin / admin123，首次登录后请修改密码。</p>
    </section>
  </main>

  <main v-else class="admin-layout">
    <aside class="sidebar">
      <div class="brand">
        <p class="eyebrow">青玄</p>
        <h2>商业管理后台</h2>
      </div>
      <el-menu class="side-menu" :default-active="tab" @select="tab = $event">
        <el-menu-item index="users">用户管理</el-menu-item>
        <el-menu-item index="jobs">任务监控</el-menu-item>
        <el-menu-item index="support">客服与价格</el-menu-item>
        <el-menu-item index="records">积分记录</el-menu-item>
        <el-menu-item index="password">修改密码</el-menu-item>
      </el-menu>
      <el-button class="logout" @click="logout">退出登录</el-button>
    </aside>

    <section class="content">
      <header class="page-head">
        <div>
          <p class="eyebrow">Admin Console</p>
          <h1>{{ pageTitle }}</h1>
        </div>
        <el-button v-if="tab === 'users'" type="primary" @click="openCreateUser">新建用户</el-button>
      </header>

      <section v-if="tab === 'users'" class="panel">
        <div class="stat-grid">
          <div class="stat-card">
            <span>用户数量</span>
            <strong>{{ users.length }}</strong>
          </div>
          <div class="stat-card">
            <span>账户总积分</span>
            <strong>{{ totalCredits }}</strong>
          </div>
          <div class="stat-card">
            <span>当前规则</span>
            <strong>干声 {{ config.voice_train_cost }} / 歌曲 {{ config.song_process_cost }}</strong>
          </div>
        </div>
        <div class="toolbar">
          <el-input v-model="phone" placeholder="输入手机号搜索用户" clearable @keyup.enter="loadUsers" />
          <el-button @click="loadUsers">搜索</el-button>
        </div>
        <el-table :data="users" border stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="phone" label="手机号" />
          <el-table-column prop="credits" label="训练积分" width="110" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="300">
            <template #default="{ row }">
              <el-button size="small" @click="openEditUser(row)">编辑</el-button>
              <el-button size="small" @click="resetPassword(row)">重置密码</el-button>
              <el-button size="small" type="primary" @click="addCredits(row)">加积分</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section v-if="tab === 'jobs'" class="panel">
        <div class="stat-grid five-grid">
          <div class="stat-card">
            <span>总任务数</span>
            <strong>{{ jobs.length }}</strong>
          </div>
          <div class="stat-card running-card">
            <span>正在运行 (GPU加速)</span>
            <strong style="color: #4f46e5;">{{ runningJobsCount }}</strong>
          </div>
          <div class="stat-card queued-card">
            <span>排队等待</span>
            <strong style="color: #e6a23c;">{{ queuedJobsCount }}</strong>
          </div>
          <div class="stat-card paused-card">
            <span>已暂停</span>
            <strong style="color: #909399;">{{ pausedJobsCount }}</strong>
          </div>
          <div class="stat-card success-card">
            <span>执行成功</span>
            <strong style="color: #10b981;">{{ successJobsCount }}</strong>
          </div>
        </div>

        <div class="toolbar" style="max-width: 1000px; flex-wrap: wrap;">
          <el-input v-model="jobSearch" placeholder="搜索任务ID / 用户名 / 手机号" clearable style="width: 260px;" @keyup.enter="loadJobs" />
          <el-select v-model="jobStatusFilter" clearable placeholder="任务状态" style="width: 140px;" @change="loadJobs">
            <el-option label="全部状态" value="" />
            <el-option label="正在运行" value="running" />
            <el-option label="排队中" value="queued" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
          </el-select>
          <el-select v-model="jobTypeFilter" clearable placeholder="任务类型" style="width: 160px;" @change="loadJobs">
            <el-option label="全部类型" value="" />
            <el-option label="声音克隆训练" value="voice_train" />
            <el-option label="歌曲一键合成" value="song_process" />
          </el-select>
          <el-button @click="loadJobs">刷新</el-button>
          <el-switch v-model="autoRefreshJobs" active-text="实时监控(3秒)" style="margin-left: 10px;" />
        </div>

        <el-table :data="jobs" border stripe style="width: 100%;">
          <el-table-column prop="id" label="ID" width="70" align="center" />
          <el-table-column label="所属用户" width="160">
            <template #default="{ row }">
              <div style="font-weight: 600;">{{ row.username || '匿名用户' }}</div>
              <div class="muted" style="font-size: 12px;">{{ row.phone || '-' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="任务类型" width="130" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.type === 'voice_train'" effect="light" type="primary">干声训练</el-tag>
              <el-tag v-else-if="row.type === 'song_process'" effect="light" type="success">歌曲合成</el-tag>
              <el-tag v-else effect="light" type="info">{{ row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'running'" type="warning" effect="dark">运行中</el-tag>
              <el-tag v-else-if="row.status === 'queued'" type="info" effect="plain">排队中</el-tag>
              <el-tag v-else-if="row.status === 'paused'" type="info" effect="dark" style="background: #909399; border-color: #909399; color: #fff;">已暂停</el-tag>
              <el-tag v-else-if="row.status === 'cancelled'" type="info" effect="plain" style="color: #909399;">已取消</el-tag>
              <el-tag v-else-if="row.status === 'success'" type="success" effect="dark">成功</el-tag>
              <el-tag v-else-if="row.status === 'failed'" type="danger" effect="dark">失败</el-tag>
              <el-tag v-else>{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度" min-width="180">
            <template #default="{ row }">
              <el-progress
                :percentage="row.progress || 0"
                :status="row.status === 'failed' ? 'exception' : (row.status === 'success' ? 'success' : '')"
                :stroke-width="14"
                :text-inside="true"
              />
              <div v-if="row.error_message" style="color: #f56c6c; font-size: 12px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="row.error_message">
                失败: {{ row.error_message }}
              </div>
              <div v-else-if="row.status === 'running'" class="muted" style="font-size: 12px; margin-top: 4px;">
                RTX 3080 Ti 本地加速计算中...
              </div>
              <div v-else-if="row.status === 'paused'" class="muted" style="font-size: 12px; margin-top: 4px; color: #909399;">
                任务已暂停，计算资源已释放
              </div>
            </template>
          </el-table-column>
          <el-table-column label="任务产出 / 目标" min-width="160">
            <template #default="{ row }">
              <div v-if="row.output_path" style="font-family: monospace; font-size: 12px; word-break: break-all;" :title="row.output_path">
                {{ formatOutputPath(row.output_path) }}
              </div>
              <div v-else-if="row.payload" class="muted" style="font-size: 12px;">
                {{ getPayloadSummary(row.payload) }}
              </div>
              <div v-else class="muted">-</div>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">
              <span style="font-size: 13px;">{{ formatDateTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" align="center">
            <template #default="{ row }">
              <el-button size="small" @click="viewJobDetail(row)">详情</el-button>
              <el-button v-if="row.status === 'running' || row.status === 'queued'" size="small" type="warning" plain @click="pauseJob(row)">暂停</el-button>
              <el-button v-if="row.status === 'paused'" size="small" type="success" plain @click="resumeJob(row)">恢复</el-button>
              <el-button v-if="row.status === 'running' || row.status === 'queued' || row.status === 'paused'" size="small" type="danger" plain @click="cancelJob(row)">取消</el-button>
              <el-button v-if="row.status === 'failed' || row.status === 'cancelled'" size="small" type="warning" @click="retryJob(row)">重试</el-button>
              <el-button size="small" type="danger" text @click="deleteJob(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section v-if="tab === 'support'" class="two-column">
        <el-form label-width="140px" class="panel form-panel support-card">
          <div class="section-head">
            <div>
              <p class="eyebrow">Support</p>
              <h3>客服信息</h3>
            </div>
          </div>
          <div class="qr-preview">
            <span v-if="!support.qr_code_url">二维码预览</span>
            <img v-else :src="support.qr_code_url" alt="客服二维码" />
          </div>
          <el-form-item label="客服名称"><el-input v-model="support.name" /></el-form-item>
          <el-form-item label="二维码地址"><el-input v-model="support.qr_code_url" /></el-form-item>
          <el-form-item label="二维码上传">
            <el-upload :http-request="uploadQr" :show-file-list="false">
              <el-button>上传二维码</el-button>
            </el-upload>
          </el-form-item>
          <el-button type="primary" @click="saveSupport">保存客服信息</el-button>
        </el-form>

        <el-form label-width="150px" class="panel form-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">Pricing</p>
              <h3>积分价格与消耗</h3>
            </div>
          </div>
          <div class="rule-strip">
            <span>1积分 = {{ config.recharge_price_per_credit }}元</span>
            <span>干声 {{ config.voice_train_cost }}积分</span>
            <span>歌曲 {{ config.song_process_cost }}积分</span>
            <span>每日免费 {{ config.daily_free_credits ?? 0 }}次</span>
          </div>
          <el-form-item label="注册送积分"><el-input-number v-model="config.signup_bonus_credits" :min="0" /></el-form-item>
          <el-form-item label="干声训练消耗"><el-input-number v-model="config.voice_train_cost" :min="0" /></el-form-item>
          <el-form-item label="歌曲处理消耗"><el-input-number v-model="config.song_process_cost" :min="0" /></el-form-item>
          <el-form-item label="每日免费额度">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-input-number v-model="config.daily_free_credits" :min="0" />
              <span class="muted" style="font-size: 12px;">次/天（每天0点重置，不累积）</span>
            </div>
          </el-form-item>
          <el-form-item label="每积分价格"><el-input-number v-model="config.recharge_price_per_credit" :min="0" /></el-form-item>
          <el-button type="primary" @click="saveSupport">保存价格配置</el-button>
        </el-form>
      </section>

      <section v-if="tab === 'records'" class="panel">
        <div class="stat-grid records-stats">
          <div class="stat-card">
            <span>记录数量</span>
            <strong>{{ records.length }}</strong>
          </div>
          <div class="stat-card">
            <span>充值合计</span>
            <strong>{{ rechargeTotal }}</strong>
          </div>
          <div class="stat-card">
            <span>消费合计</span>
            <strong>{{ consumeTotal }}</strong>
          </div>
        </div>
        <div class="toolbar">
          <el-select v-model="recordType" clearable placeholder="记录类型">
            <el-option label="充值记录" value="recharge" />
            <el-option label="消费记录" value="consume" />
          </el-select>
          <el-button @click="loadRecords">刷新</el-button>
        </div>
        <el-table :data="records" border stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="user_id" label="用户ID" width="100" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="amount" label="积分变化" width="120" />
          <el-table-column prop="balance_after" label="余额" width="100" />
          <el-table-column prop="note" label="备注" />
          <el-table-column prop="created_at" label="时间" />
        </el-table>
      </section>

      <section v-if="tab === 'password'" class="panel narrow">
        <el-form label-width="120px">
          <el-form-item label="旧密码"><el-input v-model="passwordForm.old_password" show-password /></el-form-item>
          <el-form-item label="新密码"><el-input v-model="passwordForm.new_password" show-password /></el-form-item>
          <el-button type="primary" @click="changePassword">修改密码</el-button>
        </el-form>
      </section>
    </section>

    <el-dialog v-model="userDialog.visible" :title="userDialog.mode === 'create' ? '新建用户' : '编辑用户'" width="520px">
      <el-form label-width="110px">
        <p class="dialog-note">创建账号后，用户可使用客户端登录。初始积分默认读取当前产品配置，也可以手动调整。</p>
        <el-form-item label="用户名">
          <el-input v-model="userForm.username" :disabled="userDialog.mode === 'edit'" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item v-if="userDialog.mode === 'create'" label="登录密码">
          <el-input v-model="userForm.password" show-password placeholder="请输入初始密码" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="userForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="训练积分">
          <el-input-number v-model="userForm.credits" :min="0" />
        </el-form-item>
        <el-form-item v-if="userDialog.mode === 'edit'" label="状态">
          <el-select v-model="userForm.status">
            <el-option label="active" value="active" />
            <el-option label="disabled" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitUserDialog">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="jobDetailDialog.visible" title="任务详情" width="680px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">{{ currentJob?.id }}</el-descriptions-item>
        <el-descriptions-item label="任务类型">{{ currentJob?.type }}</el-descriptions-item>
        <el-descriptions-item label="所属用户">{{ currentJob?.username || '未关联' }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ currentJob?.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ currentJob?.status }}</el-descriptions-item>
        <el-descriptions-item label="当前进度">{{ currentJob?.progress }}%</el-descriptions-item>
        <el-descriptions-item label="锁定执行器" :span="2">{{ currentJob?.locked_by || '无' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ formatDateTime(currentJob?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="产出路径" :span="2">
          <code style="word-break: break-all; font-size: 12px;">{{ currentJob?.output_path || '无' }}</code>
        </el-descriptions-item>
        <el-descriptions-item v-if="currentJob?.error_message" label="错误信息" :span="2">
          <div style="color: #f56c6c; white-space: pre-wrap; font-family: monospace; max-height: 200px; overflow-y: auto; font-size: 12px;">{{ currentJob?.error_message }}</div>
        </el-descriptions-item>
      </el-descriptions>
      <div v-if="currentJob?.payload" style="margin-top: 15px;">
        <p style="font-weight: 600; margin-bottom: 6px; font-size: 13px;">任务参数 (Payload):</p>
        <pre style="background: #f8fafc; padding: 10px; border-radius: 6px; font-size: 12px; max-height: 200px; overflow-y: auto; border: 1px solid #e2e8f0;">{{ JSON.stringify(currentJob.payload, null, 2) }}</pre>
      </div>
      <template #footer>
        <el-button @click="jobDetailDialog.visible = false">关闭</el-button>
        <el-button v-if="currentJob?.status === 'failed'" type="warning" @click="retryJob(currentJob)">重试此任务</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200' })
const token = ref(localStorage.getItem('admin_token') || '')
const tab = ref('users')
const phone = ref('')
const users = ref([])
const records = ref([])
const recordType = ref('')

// 任务管理状态
const jobs = ref([])
const jobSearch = ref('')
const jobStatusFilter = ref('')
const jobTypeFilter = ref('')
const autoRefreshJobs = ref(true)
const jobDetailDialog = reactive({ visible: false })
const currentJob = ref(null)
let refreshTimer = null

const loginForm = reactive({ username: 'admin', password: 'xxxx' })
const passwordForm = reactive({ old_password: '', new_password: '' })
const config = reactive({ signup_bonus_credits: 480, voice_train_cost: 450, song_process_cost: 1, recharge_price_per_credit: 1, daily_free_credits: 5 })
const support = reactive({ name: '', qr_code_url: '' })
const userDialog = reactive({ visible: false, mode: 'create', userId: null })
const userForm = reactive({ username: '', password: '', phone: '', credits: 480, status: 'active' })

const pageTitle = computed(() => ({
  users: '用户管理',
  jobs: '任务管理 (本地训练与合成监控)',
  support: '客服与价格',
  records: '积分记录',
  password: '修改密码'
}[tab.value]))

const totalCredits = computed(() => users.value.reduce((sum, user) => sum + Number(user.credits || 0), 0))
const rechargeTotal = computed(() => records.value.filter(row => row.type === 'recharge').reduce((sum, row) => sum + Number(row.amount || 0), 0))
const consumeTotal = computed(() => Math.abs(records.value.filter(row => row.type === 'consume').reduce((sum, row) => sum + Number(row.amount || 0), 0)))

const runningJobsCount = computed(() => jobs.value.filter(j => j.status === 'running').length)
const queuedJobsCount = computed(() => jobs.value.filter(j => j.status === 'queued').length)
const pausedJobsCount = computed(() => jobs.value.filter(j => j.status === 'paused').length)
const successJobsCount = computed(() => jobs.value.filter(j => j.status === 'success').length)

api.interceptors.request.use((request) => {
  if (token.value) request.headers.Authorization = `Bearer ${token.value}`
  return request
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      token.value = ''
      localStorage.removeItem('admin_token')
    }
    return Promise.reject(error)
  }
)

async function login() {
  try {
    const { data } = await api.post('/api/admin/login', loginForm)
    token.value = data.token
    localStorage.setItem('admin_token', token.value)
    await Promise.all([loadUsers(), loadSupport(), loadRecords(), loadJobs()])
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '账号或密码错误')
  }
}
function logout() {
  token.value = ''
  localStorage.removeItem('admin_token')
}
async function loadUsers() {
  try {
    users.value = (await api.get('/api/admin/users', { params: { phone: phone.value } })).data
  } catch (error) {
    console.error('loadUsers error:', error)
  }
}

// 任务管理 API 方法
async function loadJobs() {
  try {
    const params = {}
    if (jobStatusFilter.value) params.status = jobStatusFilter.value
    if (jobTypeFilter.value) params.type = jobTypeFilter.value
    if (jobSearch.value) params.search = jobSearch.value
    const res = await api.get('/api/admin/jobs', { params })
    jobs.value = res.data
  } catch (error) {
    console.error('loadJobs error:', error)
  }
}

function viewJobDetail(job) {
  currentJob.value = job
  jobDetailDialog.visible = true
}

async function pauseJob(job) {
  try {
    await api.post(`/api/admin/jobs/${job.id}/pause`)
    ElMessage.success(`任务 #${job.id} 已暂停`)
    loadJobs()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '暂停失败')
  }
}

async function resumeJob(job) {
  try {
    await api.post(`/api/admin/jobs/${job.id}/resume`)
    ElMessage.success(`任务 #${job.id} 已恢复排队`)
    loadJobs()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '恢复失败')
  }
}

async function cancelJob(job) {
  try {
    await ElMessageBox.confirm(`确定取消任务 #${job.id} 吗？取消后该任务将停止执行。`, '取消确认', { type: 'warning' })
    await api.post(`/api/admin/jobs/${job.id}/cancel`)
    ElMessage.success(`任务 #${job.id} 已取消`)
    loadJobs()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('取消失败')
  }
}

async function retryJob(job) {
  try {
    await api.post(`/api/admin/jobs/${job.id}/retry`)
    ElMessage.success(`任务 #${job.id} 已重置排队`)
    if (jobDetailDialog.visible) jobDetailDialog.visible = false
    loadJobs()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '重试失败')
  }
}


async function deleteJob(job) {
  try {
    await ElMessageBox.confirm(`确定删除任务 #${job.id} 吗？`, '删除确认', { type: 'warning' })
    await api.delete(`/api/admin/jobs/${job.id}`)
    ElMessage.success('任务已删除')
    loadJobs()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

function formatDateTime(val) {
  if (!val) return '-'
  try {
    return new Date(val).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return val
  }
}

function formatOutputPath(path) {
  if (!path) return '-'
  const parts = path.split(/[\/\\]/)
  return parts.slice(-2).join('/')
}

function getPayloadSummary(payload) {
  if (!payload || typeof payload !== 'object') return '-'
  if (payload.voice_model_name) return `模型: ${payload.voice_model_name} (Epochs: ${payload.total_epoch || 50})`
  if (payload.song_name) return `歌曲: ${payload.song_name}`
  return JSON.stringify(payload)
}

function openCreateUser() {
  Object.assign(userForm, { username: '', password: '', phone: '', credits: config.signup_bonus_credits || 480, status: 'active' })
  Object.assign(userDialog, { visible: true, mode: 'create', userId: null })
}
function openEditUser(row) {
  Object.assign(userForm, { username: row.username, password: '', phone: row.phone, credits: row.credits, status: row.status })
  Object.assign(userDialog, { visible: true, mode: 'edit', userId: row.id })
}
async function submitUserDialog() {
  if (userDialog.mode === 'create') {
    await api.post('/api/admin/users', {
      username: userForm.username,
      password: userForm.password,
      phone: userForm.phone,
      credits: userForm.credits
    })
    ElMessage.success('用户已创建')
  } else {
    await api.put(`/api/admin/users/${userDialog.userId}`, {
      phone: userForm.phone,
      credits: userForm.credits,
      status: userForm.status
    })
    ElMessage.success('用户已保存')
  }
  userDialog.visible = false
  loadUsers()
}
async function resetPassword(row) {
  const password = await ElMessageBox.prompt('新密码', `重置 ${row.username} 的密码`)
  await api.post(`/api/admin/users/${row.id}/reset-password`, { password: password.value })
  ElMessage.success('已重置')
}
async function addCredits(row) {
  const amount = await ElMessageBox.prompt('增加积分', `给 ${row.username} 充值`)
  await api.post(`/api/admin/users/${row.id}/credits`, { amount: Number(amount.value), note: '后台充值' })
  loadUsers()
}
async function loadSupport() {
  Object.assign(config, (await api.get('/api/admin/config')).data)
  Object.assign(support, (await api.get('/api/admin/support')).data)
}
async function saveSupport() {
  await api.put('/api/admin/config', config)
  await api.put('/api/admin/support', support)
  ElMessage.success('已保存')
}
async function uploadQr(options) {
  try {
    const file = options.file
    const contentType = file.type || 'application/octet-stream'
    const { data } = await api.post('/api/admin/oss/presign-upload', {
      category: 'support_qr',
      filename: file.name,
      content_type: contentType
    })
    await axios.put(data.upload_url, file, { headers: data.headers || { 'Content-Type': contentType } })
    support.qr_code_url = data.public_url
    await api.put('/api/admin/support', support)
    options.onSuccess?.(data)
    ElMessage.success('二维码已上传')
  } catch (error) {
    options.onError?.(error)
    ElMessage.error('二维码上传失败')
  }
}
async function loadRecords() {
  records.value = (await api.get('/api/admin/credit-transactions', { params: { transaction_type: recordType.value } })).data
}
async function changePassword() {
  await api.post('/api/admin/password', passwordForm)
  ElMessage.success('密码已修改，请重新登录')
  logout()
}

onMounted(() => {
  if (token.value) {
    Promise.all([loadUsers(), loadSupport(), loadRecords(), loadJobs()])
  }
  refreshTimer = setInterval(() => {
    if (token.value && tab.value === 'jobs' && autoRefreshJobs.value) {
      loadJobs()
    }
  }, 3000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>
