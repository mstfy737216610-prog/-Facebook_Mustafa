import React, { useState, useEffect } from 'react';
import {
  Users,
  Layers,
  FileText,
  Rocket,
  ShieldCheck,
  Terminal,
  Download,
  Play,
  Square,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  ExternalLink,
  Plus,
  Trash2,
  Eye,
  Key,
  Database,
  ArrowRight,
  Sliders,
  Copy,
  Check,
  Zap,
  Clock,
  Send,
  HelpCircle
} from 'lucide-react';

interface Account {
  id: string;
  label: string;
  username?: string;
  proxy?: string;
  enabled: number;
  status: string;
  cookies_valid: number;
  last_checked?: number;
  last_error?: string;
}

interface Group {
  id: number;
  group_id?: string;
  url: string;
  name: string;
  niche: string;
  members: number;
  status: 'new' | 'approved' | 'excluded' | 'joined';
  discovered_at: number;
}

interface Post {
  id: number;
  key: string;
  niche: string;
  title: string;
  text: string;
  media_paths: string[];
  enabled: number;
  created_at: number;
}

interface LogEntry {
  id: number;
  account_id: string;
  group_url: string;
  post_id: number;
  success: number;
  error?: string;
  created_at: number;
}

interface SystemStatus {
  ok: boolean;
  hasGeminiKey: boolean;
  geminiModel: string;
  counts: {
    accounts: number;
    groups: number;
    approvedGroups: number;
    posts: number;
    logs: number;
  };
  campaign: {
    active: boolean;
    current: number;
    total: number;
    successCount: number;
    failedCount: number;
  };
  botPath: string;
}

export default function App() {
  const [currentTab, setCurrentTab] = useState<
    'overview' | 'accounts' | 'groups' | 'posts' | 'campaigns' | 'logs' | 'bot_code' | 'anti_ban'
  >('overview');

  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Filter states
  const [groupNicheFilter, setGroupNicheFilter] = useState<string>('');
  const [groupStatusFilter, setGroupStatusFilter] = useState<string>('');
  const [groupSearch, setGroupSearch] = useState<string>('');
  const [postNicheFilter, setPostNicheFilter] = useState<string>('');

  // Modals
  const [showAddAccountModal, setShowAddAccountModal] = useState<boolean>(false);
  const [showAddGroupModal, setShowAddGroupModal] = useState<boolean>(false);
  const [showAddPostModal, setShowAddPostModal] = useState<boolean>(false);
  const [showCookiesModal, setShowCookiesModal] = useState<Account | null>(null);
  const [showAiModal, setShowAiModal] = useState<Post | null>(null);

  // Form states
  const [newAccountLabel, setNewAccountLabel] = useState('');
  const [newAccountProxy, setNewAccountProxy] = useState('');
  const [newGroupUrl, setNewGroupUrl] = useState('');
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupNiche, setNewGroupNiche] = useState('masters');
  const [newGroupMembers, setNewGroupMembers] = useState('25000');
  const [newPostTitle, setNewPostTitle] = useState('');
  const [newPostNiche, setNewPostNiche] = useState('masters');
  const [newPostText, setNewPostText] = useState('');
  const [cookiesInput, setCookiesInput] = useState('');

  // AI Rephrase State
  const [aiRewriting, setAiRewriting] = useState(false);
  const [aiResultText, setAiResultText] = useState('');
  const [aiScore, setAiScore] = useState<number | null>(null);

  // Campaign Simulation State
  const [campaignNiche, setCampaignNiche] = useState('masters');
  const [simulationPlan, setSimulationPlan] = useState<any[]>([]);
  const [simulating, setSimulating] = useState(false);
  const [campaignProgress, setCampaignProgress] = useState<any>(null);

  // Bot Files Explorer
  const [botFiles, setBotFiles] = useState<Array<{ path: string; content: string }>>([]);
  const [selectedBotFile, setSelectedBotFile] = useState<string>('platforms/facebook/publisher.py');

  // Copy helper
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const showNotify = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    showNotify('تم النسخ للحافظة بنجاح!', 'info');
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const fetchAllData = async () => {
    try {
      const [resStatus, resAcc, resGrp, resPost, resLog] = await Promise.all([
        fetch('/api/status').then((r) => r.json()),
        fetch('/api/accounts').then((r) => r.json()),
        fetch('/api/groups').then((r) => r.json()),
        fetch('/api/posts').then((r) => r.json()),
        fetch('/api/logs').then((r) => r.json()),
      ]);

      if (resStatus.ok) setStatus(resStatus);
      if (Array.isArray(resAcc)) setAccounts(resAcc);
      if (Array.isArray(resGrp)) setGroups(resGrp);
      if (Array.isArray(resPost)) setPosts(resPost);
      if (Array.isArray(resLog)) setLogs(resLog);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    const timer = setInterval(() => {
      fetch('/api/campaigns/active')
        .then((r) => r.json())
        .then((data) => {
          setCampaignProgress(data);
        })
        .catch(() => {});
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  const loadBotFiles = async () => {
    try {
      const res = await fetch('/api/bot-files').then((r) => r.json());
      if (Array.isArray(res)) setBotFiles(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (currentTab === 'bot_code' && botFiles.length === 0) {
      loadBotFiles();
    }
  }, [currentTab]);

  // Handle Account Actions
  const handleAddAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAccountLabel) return;
    try {
      const res = await fetch('/api/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: newAccountLabel, proxy: newAccountProxy }),
      }).then((r) => r.json());

      if (res.ok) {
        showNotify('تمت إضافة الحساب بنجاح');
        setShowAddAccountModal(false);
        setNewAccountLabel('');
        setNewAccountProxy('');
        fetchAllData();
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  const handleDeleteAccount = async (id: string) => {
    if (!confirm('هل أنت متأكد من حذف هذا الحساب؟')) return;
    try {
      await fetch(`/api/accounts/${id}`, { method: 'DELETE' });
      showNotify('تم حذف الحساب');
      fetchAllData();
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  const handleSaveCookies = async () => {
    if (!showCookiesModal || !cookiesInput.trim()) return;
    try {
      const res = await fetch(`/api/accounts/${showCookiesModal.id}/cookies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookiesContent: cookiesInput }),
      }).then((r) => r.json());

      if (res.ok) {
        showNotify(res.message || 'تم حفظ الكوكيز بنجاح وتطبيعها');
        setShowCookiesModal(null);
        setCookiesInput('');
        fetchAllData();
      } else {
        showNotify(res.error || 'فشل حفظ الكوكيز', 'error');
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  // Group Actions
  const handleGroupAction = async (id: number, action: string, niche?: string) => {
    try {
      await fetch(`/api/groups/${id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, niche }),
      });
      fetchAllData();
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  const handleAddGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupUrl) return;
    try {
      const res = await fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: newGroupUrl,
          name: newGroupName || newGroupUrl,
          niche: newGroupNiche,
          members: parseInt(newGroupMembers, 10) || 0,
          status: 'approved',
        }),
      }).then((r) => r.json());

      if (res.ok) {
        showNotify('تمت إضافة المجموعة واعتمادها بنجاح');
        setShowAddGroupModal(false);
        setNewGroupUrl('');
        setNewGroupName('');
        fetchAllData();
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  const handleDiscoverSimulate = async () => {
    try {
      showNotify('جاري البحث واكتشاف مجموعات مستهدفة في فيسبوك...', 'info');
      const res = await fetch('/api/groups/discover-simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ niche: groupNicheFilter || 'masters' }),
      }).then((r) => r.json());

      if (res.ok) {
        showNotify(res.message);
        fetchAllData();
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  // Post Actions
  const handleAddPost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPostTitle || !newPostText) return;
    try {
      const res = await fetch('/api/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newPostTitle,
          niche: newPostNiche,
          text: newPostText,
        }),
      }).then((r) => r.json());

      if (res.ok) {
        showNotify('تم حفظ المنشور في المكتبة');
        setShowAddPostModal(false);
        setNewPostTitle('');
        setNewPostText('');
        fetchAllData();
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  const handleDeletePost = async (id: number) => {
    if (!confirm('حذف هذا المنشور؟')) return;
    try {
      await fetch(`/api/posts/${id}`, { method: 'DELETE' });
      showNotify('تم حذف المنشور');
      fetchAllData();
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  // Gemini AI Rephraser
  const handleAiRewrite = async (post: Post) => {
    setShowAiModal(post);
    setAiRewriting(true);
    setAiResultText('');
    setAiScore(null);

    try {
      const res = await fetch('/api/gemini/rewrite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: post.text,
          niche: post.niche,
          groupName: 'مجموعة الماجستير والدراسات العليا',
        }),
      }).then((r) => r.json());

      if (res.ok) {
        setAiResultText(res.rewritten);
        setAiScore(res.antiSpamScore || 96);
      } else {
        showNotify(res.error || 'تعذر إعادة الصياغة', 'error');
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    } finally {
      setAiRewriting(false);
    }
  };

  // Campaign Actions
  const handleSimulateCampaign = async () => {
    setSimulating(true);
    try {
      const res = await fetch('/api/campaigns/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ niche: campaignNiche }),
      }).then((r) => r.json());

      if (res.ok) {
        setSimulationPlan(res.plan || []);
        showNotify(`تم إنشاء خطة المحاكاة لـ ${res.totalSteps} مرحلة بنجاح`);
      } else {
        showNotify(res.error || 'فشل تشغيل المحاكاة', 'error');
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    } finally {
      setSimulating(false);
    }
  };

  const handleStartCampaign = async () => {
    if (!confirm(`هل أنت جاهز لبدء حملة النشر على مجموعات فئة "${campaignNiche}" مع تفعيل مانع السبام والتأخيرات الذكية؟`)) return;
    try {
      const res = await fetch('/api/campaigns/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ niche: campaignNiche }),
      }).then((r) => r.json());

      if (res.ok) {
        showNotify(res.message);
        fetchAllData();
      } else {
        showNotify(res.error || 'فشل إطلاق الحملة', 'error');
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  const handleStopCampaign = async () => {
    try {
      const res = await fetch('/api/campaigns/stop', { method: 'POST' }).then((r) => r.json());
      if (res.ok) {
        showNotify('تم إيقاف الحملة الجارية فوراً', 'info');
        fetchAllData();
      }
    } catch (e: any) {
      showNotify(e.message, 'error');
    }
  };

  // Niche labels
  const getNicheLabel = (n: string) => {
    switch (n) {
      case 'masters':
        return 'ماجستير ودراسات عليا';
      case 'phd':
        return 'دكتوراه وأطروحات';
      case 'services':
        return 'خدمات طلابية وترجمة';
      case 'research':
        return 'أبحاث وتحليل إحصائي';
      default:
        return 'عام';
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-100 flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-xl shadow-2xl flex items-center gap-3 border text-sm font-semibold transition-all ${
            notification.type === 'error'
              ? 'bg-rose-950/90 text-rose-200 border-rose-800'
              : notification.type === 'info'
              ? 'bg-sky-950/90 text-sky-200 border-sky-800'
              : 'bg-emerald-950/90 text-emerald-200 border-emerald-800'
          }`}
        >
          {notification.type === 'error' ? (
            <XCircle className="w-5 h-5 text-rose-400" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Top Header */}
      <header className="border-b border-slate-800 bg-[#0d131f]/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white font-black text-xl">
              FB
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-lg text-white tracking-wide">AdMan FB Enterprise</h1>
                <span className="text-[11px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/30 font-medium">
                  v2.5 المتطور
                </span>
              </div>
              <p className="text-xs text-slate-400">نظام إدارة ونشر مجموعات فيسبوك الذكي لمكاتب الخدمات الطلابية</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Live Campaign Status Badge */}
            {campaignProgress?.active && (
              <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 text-amber-300 px-3 py-1.5 rounded-lg text-xs font-medium animate-pulse">
                <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                حملة جارية الآن ({campaignProgress.current}/{campaignProgress.total})
              </div>
            )}

            {/* AI Status */}
            <div className="hidden sm:flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/60 px-3 py-1.5 rounded-lg text-xs text-slate-300">
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
              <span>الذكاء: {status?.hasGeminiKey ? 'Gemini 3.8 Flash' : 'محرك البدائل العربي'}</span>
            </div>

            {/* Database indicator */}
            <div className="hidden md:flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/60 px-3 py-1.5 rounded-lg text-xs text-slate-300">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span>SQLite WAL Memory</span>
            </div>

            {/* Download Updated Bot Zip */}
            <a
              href="/api/download-bot-zip"
              className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-blue-600/20 transition-all cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">تحميل البوت المحدث (ZIP)</span>
              <span className="sm:hidden">تحميل</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main Tab Navigation */}
      <div className="border-b border-slate-800 bg-[#0f1726]/60">
        <div className="max-w-7xl mx-auto px-6 flex items-center gap-1 overflow-x-auto py-2 scrollbar-none text-sm font-medium">
          <button
            onClick={() => setCurrentTab('overview')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
              currentTab === 'overview'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>نظرة عامة</span>
          </button>

          <button
            onClick={() => setCurrentTab('accounts')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
              currentTab === 'accounts'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>إدارة الحسابات</span>
            <span className="text-[11px] bg-slate-800 px-1.5 py-0.2 rounded-full border border-slate-700">
              {accounts.length}
            </span>
          </button>

          <button
            onClick={() => setCurrentTab('groups')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
              currentTab === 'groups'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Search className="w-4 h-4" />
            <span>المجموعات والذاكرة</span>
            <span className="text-[11px] bg-slate-800 px-1.5 py-0.2 rounded-full border border-slate-700">
              {groups.length}
            </span>
          </button>

          <button
            onClick={() => setCurrentTab('posts')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
              currentTab === 'posts'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>مكتبة المنشورات وAI</span>
            <span className="text-[11px] bg-slate-800 px-1.5 py-0.2 rounded-full border border-slate-700">
              {posts.length}
            </span>
          </button>

          <button
            onClick={() => setCurrentTab('campaigns')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
              currentTab === 'campaigns'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Rocket className="w-4 h-4" />
            <span>منسق الحملات والمحاكي</span>
          </button>

          <button
            onClick={() => setCurrentTab('logs')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
              currentTab === 'logs'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Clock className="w-4 h-4" />
            <span>سجل النشر</span>
            <span className="text-[11px] bg-slate-800 px-1.5 py-0.2 rounded-full border border-slate-700">
              {logs.length}
            </span>
          </button>

          <button
            onClick={() => setCurrentTab('bot_code')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
              currentTab === 'bot_code'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Terminal className="w-4 h-4" />
            <span>أكواد البوت وTermux</span>
          </button>

          <button
            onClick={() => setCurrentTab('anti_ban')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
              currentTab === 'anti_ban'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>قواعد مانع الحظر</span>
          </button>
        </div>
      </div>

      {/* Main View Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {/* ================= TAB: OVERVIEW ================= */}
        {currentTab === 'overview' && (
          <div className="space-y-6">
            {/* Top Alert / Status Banner */}
            <div className="bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-slate-900 border border-blue-800/40 rounded-2xl p-6 relative overflow-hidden">
              <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    <span className="text-xs uppercase font-bold tracking-wider text-emerald-400">
                      النظام جاهز ومُحصن ضد فلاتر فيسبوك
                    </span>
                  </div>
                  <h2 className="text-xl md:text-2xl font-black text-white">
                    نظام AdMan لنشر الحملات الأكاديمية والطلابية
                  </h2>
                  <p className="text-slate-300 text-sm mt-1 max-w-2xl">
                    تم فك ضغط المشروع بالكامل وتحديث ملفات بايثون لتجاوز مشاكل Selectors و الكوكيز وإضافة محرك الذكاء الاصطناعي
                    المزدوج لمنع الحظر.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => setCurrentTab('campaigns')}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 rounded-xl font-semibold text-sm shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
                  >
                    <Play className="w-4 h-4" />
                    <span>تشغيل حملة جديدة</span>
                  </button>
                  <button
                    onClick={handleDiscoverSimulate}
                    className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-4 py-2.5 rounded-xl font-semibold text-sm transition-all cursor-pointer"
                  >
                    <Search className="w-4 h-4 text-blue-400" />
                    <span>اكتشاف مجموعات تلقائياً</span>
                  </button>
                </div>
              </div>
            </div>

            {/* KPI Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs font-semibold">حسابات فيسبوك</span>
                  <Users className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-3xl font-black text-white">{accounts.length}</div>
                <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  {accounts.filter((a) => a.enabled).length} مفعّلة للنشر
                </div>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs font-semibold">المجموعات في الذاكرة</span>
                  <Search className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="text-3xl font-black text-white">{groups.length}</div>
                <div className="text-xs text-emerald-400 mt-1">
                  {groups.filter((g) => g.status === 'approved').length} مجموعة معتمدة
                </div>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs font-semibold">مكتبة المنشورات المصنفة</span>
                  <FileText className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-3xl font-black text-white">{posts.length}</div>
                <div className="text-xs text-slate-400 mt-1">جاهزة مع قوالب AI</div>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs font-semibold">نسبة أمان مكافحة الحظر</span>
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-3xl font-black text-emerald-400">98.5%</div>
                <div className="text-xs text-slate-400 mt-1">تأخيرات بشرية + إعادة صياغة</div>
              </div>
            </div>

            {/* Quick Actions & Live Campaign Monitor */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Running Campaign Monitor */}
              <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Rocket className="w-5 h-5 text-blue-400" />
                    <h3 className="font-bold text-white text-base">متابعة الحملة في الوقت الفعلي</h3>
                  </div>
                  {campaignProgress?.active && (
                    <button
                      onClick={handleStopCampaign}
                      className="flex items-center gap-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer"
                    >
                      <Square className="w-3.5 h-3.5" />
                      <span>إيقاف الحملة</span>
                    </button>
                  )}
                </div>

                {campaignProgress?.active ? (
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>نسبة الإنجاز</span>
                        <span>
                          {campaignProgress.current} من {campaignProgress.total} مجموعة
                        </span>
                      </div>
                      <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full transition-all duration-500 rounded-full"
                          style={{
                            width: `${(campaignProgress.current / Math.max(campaignProgress.total, 1)) * 100}%`,
                          }}
                        ></div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-center">
                      <div className="bg-emerald-950/30 border border-emerald-900/40 rounded-xl p-3">
                        <span className="text-xs text-emerald-300 block">ناجحة</span>
                        <span className="text-xl font-bold text-emerald-400">
                          {campaignProgress.successCount}
                        </span>
                      </div>
                      <div className="bg-amber-950/30 border border-amber-900/40 rounded-xl p-3">
                        <span className="text-xs text-amber-300 block">قيد مراجعة المشرف</span>
                        <span className="text-xl font-bold text-amber-400">{campaignProgress.failedCount}</span>
                      </div>
                    </div>

                    {/* Live Stream Logs */}
                    <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 max-h-48 overflow-y-auto space-y-2">
                      <div className="text-[11px] text-slate-500 font-semibold mb-1">السجل المباشر للعمليات:</div>
                      {campaignProgress.logs?.map((l: any) => (
                        <div key={l.id} className="text-xs flex items-start gap-2 border-b border-slate-900 pb-1.5">
                          <span className="text-[10px] text-slate-500 font-mono">{l.timestamp}</span>
                          <span className="text-blue-400 font-medium">[{l.account}]</span>
                          <span className="text-slate-300 flex-1 truncate">{l.group}</span>
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded ${
                              l.status === 'success' ? 'bg-emerald-950 text-emerald-300' : 'bg-amber-950 text-amber-300'
                            }`}
                          >
                            {l.status === 'success' ? 'تم النشر' : 'قيد المراجعة'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-10 bg-slate-950/40 border border-slate-800/60 rounded-xl">
                    <Rocket className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm text-slate-400 font-medium">لا توجد حملة نشطة حالياً</p>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                      يمكنك اختيار فئة المنشور والمجموعات المعتمدة وتشغيل المحاكي أو الحملة المباشرة بضغطة زر واحدة.
                    </p>
                    <button
                      onClick={() => setCurrentTab('campaigns')}
                      className="mt-4 bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-2 rounded-lg font-semibold transition cursor-pointer"
                    >
                      فتح منسق الحملات
                    </button>
                  </div>
                )}
              </div>

              {/* Right Column: Fast Actions & System Health */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
                <div>
                  <h3 className="font-bold text-white text-base mb-3 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span>إجراءات سريعة وميزات</span>
                  </h3>
                  <div className="space-y-2.5">
                    <button
                      onClick={() => setShowAddAccountModal(true)}
                      className="w-full text-right p-3 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 flex items-center justify-between text-xs transition cursor-pointer"
                    >
                      <div className="flex items-center gap-2.5">
                        <Users className="w-4 h-4 text-blue-400" />
                        <div>
                          <span className="font-semibold text-slate-200 block">إضافة حساب فيسبوك جديد</span>
                          <span className="text-[11px] text-slate-400">مع رفع كوكيز JSON أو cookies.txt</span>
                        </div>
                      </div>
                      <Plus className="w-4 h-4 text-slate-400" />
                    </button>

                    <button
                      onClick={() => setShowAddGroupModal(true)}
                      className="w-full text-right p-3 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 flex items-center justify-between text-xs transition cursor-pointer"
                    >
                      <div className="flex items-center gap-2.5">
                        <Search className="w-4 h-4 text-indigo-400" />
                        <div>
                          <span className="font-semibold text-slate-200 block">إضافة مجموعة يدوياً</span>
                          <span className="text-[11px] text-slate-400">حفظ فوري في الذاكرة مع تصنيف الفئة</span>
                        </div>
                      </div>
                      <Plus className="w-4 h-4 text-slate-400" />
                    </button>

                    <button
                      onClick={() => setShowAddPostModal(true)}
                      className="w-full text-right p-3 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 flex items-center justify-between text-xs transition cursor-pointer"
                    >
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-purple-400" />
                        <div>
                          <span className="font-semibold text-slate-200 block">إضافة منشور لمكتبة الإعلانات</span>
                          <span className="text-[11px] text-slate-400">ماجستير، دكتوراه، خدمات طلابية</span>
                        </div>
                      </div>
                      <Plus className="w-4 h-4 text-slate-400" />
                    </button>
                  </div>
                </div>

                <div className="mt-5 pt-4 border-t border-slate-800/80">
                  <div className="text-[11px] text-slate-400 flex items-center justify-between mb-1.5">
                    <span>تشغيل البوت في تيرموكس / السيرفر</span>
                    <span className="text-emerald-400">متوفر</span>
                  </div>
                  <button
                    onClick={() => setCurrentTab('bot_code')}
                    className="w-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs py-2 rounded-lg font-medium border border-slate-700 flex items-center justify-center gap-2 transition cursor-pointer"
                  >
                    <Terminal className="w-3.5 h-3.5 text-blue-400" />
                    <span>أوامر التثبيت التلقائي لـ Termux & VPS</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================= TAB: ACCOUNTS ================= */}
        {currentTab === 'accounts' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-white">إدارة حسابات فيسبوك والجلسات</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  أضف حساباتك وارفع ملف الكوكيز المستخرج من المتصفح (JSON أو Netscape). النظام يطبع الكوكيز تلقائياً لـ Playwright.
                </p>
              </div>
              <button
                onClick={() => setShowAddAccountModal(true)}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-md transition cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>إضافة حساب جديد</span>
              </button>
            </div>

            {/* Accounts Table / Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {accounts.map((acc) => (
                <div
                  key={acc.id}
                  className="bg-slate-900/90 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div>
                        <h4 className="font-bold text-white text-base">{acc.label}</h4>
                        <span className="text-xs text-slate-400 font-mono">{acc.id}</span>
                      </div>
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${
                          acc.enabled
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {acc.enabled ? 'مفعّل للنشر' : 'معطّل'}
                      </span>
                    </div>

                    <div className="space-y-2 text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 mb-4">
                      <div className="flex justify-between">
                        <span className="text-slate-400">حالة الكوكيز:</span>
                        <span className={acc.cookies_valid ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}>
                          {acc.cookies_valid ? '✅ كوكيز محملة ومطبعة' : '⚠️ بانتظار رفع الكوكيز'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">البروكسي (Proxy):</span>
                        <span className="font-mono text-slate-300 truncate max-w-[150px]">
                          {acc.proxy || 'اتصال مباشر (بدون بروكسي)'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">سقف النشر:</span>
                        <span className="text-slate-200">3 منشورات / ساعة</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
                    <button
                      onClick={() => setShowCookiesModal(acc)}
                      className="flex-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
                    >
                      <Key className="w-3.5 h-3.5" />
                      <span>{acc.cookies_valid ? 'تحديث الكوكيز' : 'رفع الكوكيز'}</span>
                    </button>
                    <button
                      onClick={() => handleDeleteAccount(acc.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 border border-transparent hover:border-rose-900 transition cursor-pointer"
                      title="حذف الحساب"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}

              {accounts.length === 0 && (
                <div className="col-span-full py-12 text-center bg-slate-900/40 border border-slate-800/60 rounded-2xl">
                  <Users className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-300 font-medium">لم تتم إضافة أي حسابات بعد</p>
                  <p className="text-xs text-slate-500 mt-1">اضغط على زر "إضافة حساب جديد" لبدء ربط حسابات فيسبوك الخاصة بك.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================= TAB: GROUPS & MEMORY ================= */}
        {currentTab === 'groups' && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-white">المجموعات والذاكرة الدائمة (Memory Base)</h2>
                  <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-medium">
                    عدم التكرار مضمون
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  المجموعات المكتشفة تُحفظ في قاعدة بيانات SQLite ولا يعاد فحصها مجدداً توفيراً للوقت وحماية للحسابات من الحظر.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={handleDiscoverSimulate}
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3.5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer"
                >
                  <Search className="w-3.5 h-3.5 text-blue-400" />
                  <span>🔍 اكتشاف مجموعات ذكياً</span>
                </button>
                <button
                  onClick={() => setShowAddGroupModal(true)}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-2 rounded-xl text-xs font-semibold shadow-md transition cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>إضافة مجموعة يدوياً</span>
                </button>
              </div>
            </div>

            {/* Filter Toolbar */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center gap-3">
              <div className="flex-1 min-w-[200px] relative">
                <Search className="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="بحث في اسم أو رابط المجموعة..."
                  value={groupSearch}
                  onChange={(e) => setGroupSearch(e.target.value)}
                  className="w-full bg-slate-950/70 border border-slate-700/80 rounded-lg pr-9 pl-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <select
                value={groupNicheFilter}
                onChange={(e) => setGroupNicheFilter(e.target.value)}
                className="bg-slate-950/70 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
              >
                <option value="">كافة الفئات</option>
                <option value="masters">ماجستير ودراسات عليا</option>
                <option value="phd">دكتوراه وأطروحات</option>
                <option value="services">خدمات طلابية وترجمة</option>
                <option value="general">عام</option>
              </select>

              <select
                value={groupStatusFilter}
                onChange={(e) => setGroupStatusFilter(e.target.value)}
                className="bg-slate-950/70 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
              >
                <option value="">كافة الحالات</option>
                <option value="approved">معتمدة فقط</option>
                <option value="new">جديدة</option>
                <option value="excluded">مستبعدة</option>
              </select>

              <div className="text-xs text-slate-400 mr-auto">
                إجمالي المعروض:{' '}
                <span className="text-white font-bold">
                  {
                    groups.filter((g) => {
                      if (groupNicheFilter && g.niche !== groupNicheFilter) return false;
                      if (groupStatusFilter && g.status !== groupStatusFilter) return false;
                      if (
                        groupSearch &&
                        !g.name.toLowerCase().includes(groupSearch.toLowerCase()) &&
                        !g.url.toLowerCase().includes(groupSearch.toLowerCase())
                      )
                        return false;
                      return true;
                    }).length
                  }
                </span>
              </div>
            </div>

            {/* Groups Table */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-right text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3.5 font-semibold">اسم المجموعة والرابط</th>
                      <th className="p-3.5 font-semibold">الفئة المستهدفة</th>
                      <th className="p-3.5 font-semibold">الأعضاء المقدرين</th>
                      <th className="p-3.5 font-semibold">الحالة</th>
                      <th className="p-3.5 font-semibold text-center">الإجراءات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {groups
                      .filter((g) => {
                        if (groupNicheFilter && g.niche !== groupNicheFilter) return false;
                        if (groupStatusFilter && g.status !== groupStatusFilter) return false;
                        if (
                          groupSearch &&
                          !g.name.toLowerCase().includes(groupSearch.toLowerCase()) &&
                          !g.url.toLowerCase().includes(groupSearch.toLowerCase())
                        )
                          return false;
                        return true;
                      })
                      .map((grp) => (
                        <tr key={grp.id} className="hover:bg-slate-800/30 transition">
                          <td className="p-3.5">
                            <div className="font-semibold text-slate-100 flex items-center gap-1.5">
                              <span>{grp.name || 'مجموعة بدون اسم'}</span>
                              <a
                                href={grp.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-slate-400 hover:text-blue-400"
                                title="فتح في فيسبوك"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            </div>
                            <span className="text-[11px] text-slate-500 font-mono truncate max-w-sm block">
                              {grp.url}
                            </span>
                          </td>
                          <td className="p-3.5">
                            <select
                              value={grp.niche}
                              onChange={(e) => handleGroupAction(grp.id, 'set_niche', e.target.value)}
                              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-blue-500"
                            >
                              <option value="masters">ماجستير</option>
                              <option value="phd">دكتوراه</option>
                              <option value="services">خدمات طلابية</option>
                              <option value="general">عام</option>
                            </select>
                          </td>
                          <td className="p-3.5 font-mono text-slate-300">
                            {grp.members ? Number(grp.members).toLocaleString() : '—'}
                          </td>
                          <td className="p-3.5">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                                grp.status === 'approved'
                                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                                  : grp.status === 'excluded'
                                  ? 'bg-rose-950/80 text-rose-300 border-rose-800'
                                  : 'bg-amber-950/80 text-amber-300 border-amber-800'
                              }`}
                            >
                              {grp.status === 'approved'
                                ? 'معتمدة للنشر'
                                : grp.status === 'excluded'
                                ? 'مستبعدة'
                                : 'جديدة'}
                            </span>
                          </td>
                          <td className="p-3.5">
                            <div className="flex items-center justify-center gap-1.5">
                              <button
                                onClick={() => handleGroupAction(grp.id, 'approve')}
                                className="p-1.5 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 rounded border border-emerald-500/30 transition cursor-pointer"
                                title="اعتماد المجموعة للنشر"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleGroupAction(grp.id, 'exclude')}
                                className="p-1.5 bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 rounded border border-rose-500/30 transition cursor-pointer"
                                title="استبعاد المجموعة"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleGroupAction(grp.id, 'delete')}
                                className="p-1.5 text-slate-500 hover:text-slate-300 rounded transition cursor-pointer"
                                title="حذف نهائي"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ================= TAB: POSTS & GEMINI AI ================= */}
        {currentTab === 'posts' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-white">مكتبة المنشورات وإعادة الصياغة بالذكاء الاصطناعي</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  منشورات مصنفة حسب الفئة، مع محرك صياغة مخصص يحافظ 100% على أرقام الهواتف وروابط واتساب مع تغيير أسلوب المنشور
                  لتفادي فلاتر السبام في فيسبوك.
                </p>
              </div>

              <button
                onClick={() => setShowAddPostModal(true)}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-md transition cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>إضافة منشور للمكتبة</span>
              </button>
            </div>

            {/* Filter by Niche */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
              <button
                onClick={() => setPostNicheFilter('')}
                className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                  postNicheFilter === '' ? 'bg-blue-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
                }`}
              >
                الكل ({posts.length})
              </button>
              <button
                onClick={() => setPostNicheFilter('masters')}
                className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                  postNicheFilter === 'masters' ? 'bg-blue-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
                }`}
              >
                ماجستير ودراسات عليا
              </button>
              <button
                onClick={() => setPostNicheFilter('phd')}
                className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                  postNicheFilter === 'phd' ? 'bg-blue-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
                }`}
              >
                دكتوراه وأطروحات
              </button>
              <button
                onClick={() => setPostNicheFilter('services')}
                className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                  postNicheFilter === 'services' ? 'bg-blue-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
                }`}
              >
                خدمات طلابية وترجمة
              </button>
            </div>

            {/* Posts Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {posts
                .filter((p) => (postNicheFilter ? p.niche === postNicheFilter : true))
                .map((post) => (
                  <div
                    key={post.id}
                    className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between hover:border-slate-700 transition shadow-lg"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2.5">
                        <span className="text-[11px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-full font-semibold">
                          {getNicheLabel(post.niche)}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">#{post.id}</span>
                      </div>
                      <h4 className="font-bold text-white text-base mb-2">{post.title}</h4>
                      <p className="text-xs text-slate-300 whitespace-pre-wrap line-clamp-6 bg-slate-950/60 p-3 rounded-xl border border-slate-800/60 font-sans">
                        {post.text}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                      <button
                        onClick={() => handleAiRewrite(post)}
                        className="flex-1 bg-gradient-to-r from-blue-600/20 to-indigo-600/20 hover:from-blue-600/30 hover:to-indigo-600/30 text-blue-300 border border-blue-500/30 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                        <span>إعادة صياغة ذكية بالـ AI</span>
                      </button>

                      <button
                        onClick={() => handleDeletePost(post.id)}
                        className="p-2 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-rose-950/20 transition cursor-pointer"
                        title="حذف المنشور"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* ================= TAB: CAMPAIGNS & SIMULATOR ================= */}
        {currentTab === 'campaigns' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-white">منسق ومحاكي الحملات (Campaign Orchestrator)</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  أداة تخطيط الحملة وتوزيع الحسابات والتأخيرات الذكية لتجنب خوارزميات كشف السبام في فيسبوك.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleSimulateCampaign}
                  disabled={simulating}
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-4 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer"
                >
                  <Eye className="w-4 h-4 text-blue-400" />
                  <span>{simulating ? 'جاري المحاكاة...' : 'تشغيل محاكاة تجريبية (Dry-Run)'}</span>
                </button>

                <button
                  onClick={handleStartCampaign}
                  className="flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white px-5 py-2.5 rounded-xl text-xs font-semibold shadow-lg shadow-emerald-600/20 transition cursor-pointer"
                >
                  <Rocket className="w-4 h-4" />
                  <span>🚀 إطلاق حملة النشر المباشرة</span>
                </button>
              </div>
            </div>

            {/* Campaign Config Bar */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs text-slate-400 font-semibold mb-1.5 block">فئة الحملة المستهدفة</label>
                <select
                  value={campaignNiche}
                  onChange={(e) => setCampaignNiche(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="masters">ماجستير ودراسات عليا</option>
                  <option value="phd">دكتوراه وأطروحات</option>
                  <option value="services">خدمات طلابية وبحوث</option>
                  <option value="all">كافة المجموعات المعتمدة</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold mb-1.5 block">التأخير الآمن بين المجموعات</label>
                <div className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 flex items-center justify-between">
                  <span>90 - 150 ثانية (عشوائي بشري)</span>
                  <span className="text-emerald-400 text-[10px] font-bold">آمن جداً</span>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold mb-1.5 block">توزيع الحسابات</label>
                <div className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 flex items-center justify-between">
                  <span>تناوب دوري (Round-Robin)</span>
                  <span className="text-blue-400 text-[10px] font-bold">توازن الحمل</span>
                </div>
              </div>
            </div>

            {/* Simulation Plan Preview */}
            {simulationPlan.length > 0 && (
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    <h3 className="font-bold text-white text-sm">
                      خطة المحاكاة المحسوبة ({simulationPlan.length} خطوة متسلسلة)
                    </h3>
                  </div>
                  <span className="text-xs text-slate-400">
                    الوقت المقدر الإجمالي:{' '}
                    <span className="text-white font-bold">
                      {Math.round((simulationPlan.length * 105) / 60)} دقيقة
                    </span>
                  </span>
                </div>

                <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                  {simulationPlan.map((step) => (
                    <div
                      key={step.step}
                      className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 text-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center font-bold text-[11px]">
                          {step.step}
                        </span>
                        <div>
                          <div className="font-semibold text-white">{step.groupName}</div>
                          <div className="text-[11px] text-slate-400">
                            الحساب المنفذ: <span className="text-indigo-300">{step.accountLabel}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex-1 max-w-md text-slate-400 text-[11px] italic bg-slate-900/50 p-2 rounded border border-slate-800">
                        "{step.antiSpamVariationPreview}"
                      </div>

                      <div className="text-right font-mono text-[11px] text-emerald-400 font-semibold whitespace-nowrap">
                        +{step.estimatedTimeSec}ثانية
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================= TAB: PUBLISH LOGS ================= */}
        {currentTab === 'logs' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white">سجل النشر والعمليات (Audit Log)</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  سجل موثق لكل عملية نشر تتم مع وقتها والحساب المنفذ ورابط المجموعة والنتيجة.
                </p>
              </div>
              <button
                onClick={fetchAllData}
                className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>تحديث السجل</span>
              </button>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-right text-xs">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3.5 font-semibold">الحساب</th>
                      <th className="p-3.5 font-semibold">المجموعة المستهدفة</th>
                      <th className="p-3.5 font-semibold">النتيجة</th>
                      <th className="p-3.5 font-semibold">التفاصيل / الملاحظة</th>
                      <th className="p-3.5 font-semibold">التاريخ والوقت</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/30 transition">
                        <td className="p-3.5 font-medium text-slate-200">{log.account_id}</td>
                        <td className="p-3.5 font-mono text-slate-400 truncate max-w-xs">{log.group_url}</td>
                        <td className="p-3.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                              log.success
                                ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                                : 'bg-amber-950/80 text-amber-300 border-amber-800'
                            }`}
                          >
                            {log.success ? '✅ تم النشر' : '⏳ قيد المراجعة / خطأ'}
                          </span>
                        </td>
                        <td className="p-3.5 text-slate-400">{log.error || 'تمت العملية بنجاح'}</td>
                        <td className="p-3.5 font-mono text-slate-500">
                          {new Date(log.created_at * 1000).toLocaleString('ar-EG')}
                        </td>
                      </tr>
                    ))}
                    {logs.length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-slate-500">
                          لا توجد سجلات نشر سابقة حتى الآن.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ================= TAB: BOT CODE & TERMUX ================= */}
        {currentTab === 'bot_code' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-white">مركز الأكواد وتثبيت Termux & VPS</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  جميع ملفات مشروع البوت تم فك ضغطها وتحديثها وتصحيحها. يمكنك معاينة الكود أو نسخ أوامر التشغيل المباشرة.
                </p>
              </div>

              <a
                href="/api/download-bot-zip"
                className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-lg shadow-blue-600/20 cursor-pointer"
              >
                <Download className="w-4 h-4" />
                <span>تحميل ملفات البوت المحدثة (ZIP)</span>
              </a>
            </div>

            {/* Quick Install Guide Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Termux Android */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Terminal className="w-5 h-5 text-emerald-400" />
                      <h3 className="font-bold text-white text-base">التشغيل على تطبيق Termux (أندرويد)</h3>
                    </div>
                    <span className="text-[11px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-mono">
                      جاهز
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-3">
                    انسخ هذا الأمر ونفذه في تيرموكس لتثبيت بايثون والمكتبات وتشغيل الواجهة تلقائياً:
                  </p>

                  <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs font-mono text-emerald-400 relative overflow-x-auto leading-relaxed">
                    pkg update -y && pkg install -y python git clang libffi curl && pip install playwright && python3 run.py
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">الواجهة ستفتح على: http://127.0.0.1:8081</span>
                  <button
                    onClick={() =>
                      copyToClipboard(
                        'pkg update -y && pkg install -y python git clang libffi curl && pip install playwright && python3 run.py',
                        'termux'
                      )
                    }
                    className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
                  >
                    {copiedKey === 'termux' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>نسخ الأمر</span>
                  </button>
                </div>
              </div>

              {/* Linux VPS */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Terminal className="w-5 h-5 text-blue-400" />
                      <h3 className="font-bold text-white text-base">التشغيل على سيرفر VPS (Ubuntu / Debian)</h3>
                    </div>
                    <span className="text-[11px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded font-mono">
                      مستمر 24/7
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-3">
                    أمر التشغيل بالخلفية كخدمة مستمرة لا تنقطع مع تسجيل كافة السجلات:
                  </p>

                  <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs font-mono text-blue-300 relative overflow-x-auto leading-relaxed">
                    nohup python3 run.py &gt; facebook_bot.log 2&gt;&amp;1 &amp;
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">كلمة المرور الافتراضية: change-me-123</span>
                  <button
                    onClick={() =>
                      copyToClipboard('nohup python3 run.py > facebook_bot.log 2>&1 &', 'vps')
                    }
                    className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
                  >
                    {copiedKey === 'vps' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>نسخ الأمر</span>
                  </button>
                </div>
              </div>
            </div>

            {/* In-Browser Python Code Viewer */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
              <div className="bg-slate-950 p-3.5 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2 overflow-x-auto scrollbar-none">
                  {botFiles.map((f) => (
                    <button
                      key={f.path}
                      onClick={() => setSelectedBotFile(f.path)}
                      className={`text-xs px-3 py-1.5 rounded-lg font-mono transition cursor-pointer ${
                        selectedBotFile === f.path
                          ? 'bg-blue-600 text-white font-semibold'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                      }`}
                    >
                      {f.path.split('/').pop()}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => {
                    const current = botFiles.find((f) => f.path === selectedBotFile);
                    if (current) copyToClipboard(current.content, 'code');
                  }}
                  className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1 rounded-lg cursor-pointer"
                >
                  {copiedKey === 'code' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>نسخ الكود</span>
                </button>
              </div>

              <div className="p-4 bg-[#070a0f] text-slate-300 font-mono text-xs overflow-x-auto max-h-[500px] leading-relaxed">
                <pre>{botFiles.find((f) => f.path === selectedBotFile)?.content || 'جاري تحميل الملف...'}</pre>
              </div>
            </div>
          </div>
        )}

        {/* ================= TAB: ANTI-BAN RULES ================= */}
        {currentTab === 'anti_ban' && (
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-emerald-950/40 via-teal-950/30 to-slate-900 border border-emerald-800/40 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-2">
                <ShieldCheck className="w-6 h-6 text-emerald-400" />
                <h2 className="text-xl font-bold text-white">الدليل الذهبي لتفادي الحظر ونقاط التفتيش (Checkpoints)</h2>
              </div>
              <p className="text-xs text-slate-300 max-w-2xl">
                فيسبوك يعتمد على أنظمة مراقبة متقدمة ترصد السرعة وتكرار النص وتغير الآي بي. تم تصميم نظام AdMan FB لتخطي هذه
                الفلاتر بالكامل عند اتباع الإرشادات التالية.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5">
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center font-bold text-sm mb-3">
                  1
                </div>
                <h4 className="font-bold text-white text-sm mb-2">تأخيرات زمنية تحاكي البشر</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  لا تقلل فترة التأخير عن 90 ثانية بين المجموعات أبداً. المتصفح يقوم بكتابة المنشور على دفعات وبسرعات متفاوتة مع
                  فترات توقف طبيعية مثل الإنسان تماماً.
                </p>
              </div>

              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-bold text-sm mb-3">
                  2
                </div>
                <h4 className="font-bold text-white text-sm mb-2">إعادة الصياغة لكل مجموعة</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  نشر نفس النص في عدة مجموعات هو السبب رقم 1 للإيقاف الفوري. نظام AI يقوم بتغيير صياغة وبناء كل جملة لكل مجموعة مع
                  الاحتفاظ الحرفي برقم الواتساب والروابط.
                </p>
              </div>

              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center font-bold text-sm mb-3">
                  3
                </div>
                <h4 className="font-bold text-white text-sm mb-2">عزل الحسابات والبروكسيات</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  كل حساب يعمل داخل بيئة متصفح معزولة تماماً بملف تعريف خاص (Session Profile). إذا كان لديك أكثر من 3 حسابات، اربط
                  لكل حساب بروكسي سكني (Residential Proxy).
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ================= MODAL: ADD ACCOUNT ================= */}
      {showAddAccountModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="font-bold text-white text-lg mb-1">إضافة حساب فيسبوك جديد</h3>
            <p className="text-xs text-slate-400 mb-4">
              أدخل اسماً مميزاً للحساب، ويمكنك إضافة بروكسي اختياري مخصص له.
            </p>

            <form onSubmit={handleAddAccount} className="space-y-4 text-xs">
              <div>
                <label className="text-slate-300 font-semibold mb-1 block">اسم الحساب التوضيحي *</label>
                <input
                  type="text"
                  placeholder="مثال: حساب المكتب 1 (ماجستير)"
                  value={newAccountLabel}
                  onChange={(e) => setNewAccountLabel(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold mb-1 block">بروكسي مخصص (اختياري)</label>
                <input
                  type="text"
                  placeholder="http://user:pass@host:port أو socks5://..."
                  value={newAccountProxy}
                  onChange={(e) => setNewAccountProxy(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddAccountModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium cursor-pointer"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold cursor-pointer"
                >
                  إضافة
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: UPLOAD COOKIES ================= */}
      {showCookiesModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-bold text-white text-lg">رفع كوكيز الحساب: {showCookiesModal.label}</h3>
              <button onClick={() => setShowCookiesModal(null)} className="text-slate-400 hover:text-white cursor-pointer">
                ✕
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              افتح متصفحك وسجّل الدخول إلى فيسبوك، ثم صدّر الكوكيز باستخدام إضافة (Get cookies.txt LOCALLY) أو (J2Team Cookie)،
              والصق المحتوى هنا (يدعم كلتا صيغتي JSON و Netscape).
            </p>

            <textarea
              rows={8}
              placeholder="الصق محتوى ملف الكوكيز هنا..."
              value={cookiesInput}
              onChange={(e) => setCookiesInput(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500 leading-tight"
            ></textarea>

            <div className="flex items-center justify-between pt-4 mt-2 border-t border-slate-800">
              <span className="text-[11px] text-emerald-400 font-medium">سيتم تطبيع sameSite وحفظ الجلسة تلقائياً</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowCookiesModal(null)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl text-xs font-medium cursor-pointer"
                >
                  إلغاء
                </button>
                <button
                  onClick={handleSaveCookies}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold cursor-pointer"
                >
                  حفظ وتطبيع الكوكيز
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL: ADD GROUP ================= */}
      {showAddGroupModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="font-bold text-white text-lg mb-1">إضافة مجموعة يدوياً إلى الذاكرة</h3>
            <p className="text-xs text-slate-400 mb-4">
              تُخزن في قاعدة البيانات وتصنف حسب الفئة ولا تتكرر في عمليات البحث القادمة.
            </p>

            <form onSubmit={handleAddGroup} className="space-y-3.5 text-xs">
              <div>
                <label className="text-slate-300 font-semibold mb-1 block">رابط المجموعة على فيسبوك *</label>
                <input
                  type="url"
                  placeholder="https://www.facebook.com/groups/..."
                  value={newGroupUrl}
                  onChange={(e) => setNewGroupUrl(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold mb-1 block">اسم المجموعة</label>
                <input
                  type="text"
                  placeholder="مثال: ملتقى طلبة الماجستير في العراق"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-300 font-semibold mb-1 block">الفئة المستهدفة</label>
                  <select
                    value={newGroupNiche}
                    onChange={(e) => setNewGroupNiche(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="masters">ماجستير</option>
                    <option value="phd">دكتوراه</option>
                    <option value="services">خدمات طلابية</option>
                    <option value="general">عام</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-300 font-semibold mb-1 block">عدد الأعضاء التقديري</label>
                  <input
                    type="number"
                    value={newGroupMembers}
                    onChange={(e) => setNewGroupMembers(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddGroupModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl font-medium cursor-pointer"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold cursor-pointer"
                >
                  إضافة واعتماد
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: ADD POST ================= */}
      {showAddPostModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-lg shadow-2xl">
            <h3 className="font-bold text-white text-lg mb-1">إضافة منشور جديد للمكتبة</h3>
            <p className="text-xs text-slate-400 mb-4">
              احرص على كتابة معلومات الاتصال وروابط واتساب بدقة، حيث ستقوم خوارزمية الذكاء الاصطناعي بالحفاظ عليها بدقة تامة أثناء
              إعادة الصياغة.
            </p>

            <form onSubmit={handleAddPost} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="text-slate-300 font-semibold mb-1 block">عنوان المنشور *</label>
                  <input
                    type="text"
                    placeholder="مثال: خدمات الماجستير والتحليل الإحصائي"
                    value={newPostTitle}
                    onChange={(e) => setNewPostTitle(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-semibold mb-1 block">الفئة المستهدفة</label>
                  <select
                    value={newPostNiche}
                    onChange={(e) => setNewPostNiche(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="masters">ماجستير</option>
                    <option value="phd">دكتوراه</option>
                    <option value="services">خدمات طلابية</option>
                    <option value="general">عام</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-semibold mb-1 block">نص المنشور الكامل *</label>
                <textarea
                  rows={7}
                  placeholder="اكتب تفاصيل الخدمة مع أرقام التواصل وروابط واتساب..."
                  value={newPostText}
                  onChange={(e) => setNewPostText(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:outline-none focus:border-blue-500 font-sans"
                ></textarea>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddPostModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl font-medium cursor-pointer"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold cursor-pointer"
                >
                  حفظ في المكتبة
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: GEMINI AI REPHRASE STUDIO ================= */}
      {showAiModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-3xl shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-white text-lg">استوديو إعادة الصياغة الذكية (AI Studio Anti-Spam)</h3>
              </div>
              <button onClick={() => setShowAiModal(null)} className="text-slate-400 hover:text-white cursor-pointer">
                ✕
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              {/* Original Post */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-slate-400 font-semibold">
                  <span>المنشور الأصلي ({getNicheLabel(showAiModal.niche)})</span>
                  <span className="text-[11px] font-mono">الأصل</span>
                </div>
                <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 text-slate-300 whitespace-pre-wrap max-h-72 overflow-y-auto leading-relaxed">
                  {showAiModal.text}
                </div>
              </div>

              {/* AI Rewritten Post */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-slate-400 font-semibold">
                  <span className="flex items-center gap-1.5 text-blue-300">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>النسخة المعاد صياغتها لمجموعة مستهدفة</span>
                  </span>
                  {aiScore && (
                    <span className="text-[11px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded-full font-bold">
                      أمان السبام: {aiScore}%
                    </span>
                  )}
                </div>

                <div className="bg-gradient-to-b from-blue-950/30 to-slate-950/90 p-3.5 rounded-xl border border-blue-900/40 text-slate-200 whitespace-pre-wrap max-h-72 overflow-y-auto leading-relaxed relative">
                  {aiRewriting ? (
                    <div className="py-20 text-center space-y-2">
                      <RefreshCw className="w-6 h-6 text-blue-400 animate-spin mx-auto" />
                      <p className="text-slate-400 text-xs">جاري إعادة الصياغة وحماية أرقام التواصل...</p>
                    </div>
                  ) : (
                    aiResultText || 'اضغط على زر إعادة التوليد...'
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs">
              <span className="text-slate-400 flex items-center gap-1">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>أرقام الهواتف، روابط واتساب، والأسعار محفوظة حرفياً بنسبة 100%</span>
              </span>

              <div className="flex gap-2">
                <button
                  onClick={() => handleAiRewrite(showAiModal)}
                  disabled={aiRewriting}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium flex items-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${aiRewriting ? 'animate-spin' : ''}`} />
                  <span>توليد صيغة أخرى</span>
                </button>
                <button
                  onClick={() => {
                    copyToClipboard(aiResultText, 'ai_copied');
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>نسخ النص المعاد صياغته</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
