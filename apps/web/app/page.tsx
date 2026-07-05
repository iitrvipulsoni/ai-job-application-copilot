'use client'

import { useState, useEffect } from 'react'

interface Job {
  id: string
  title: string
  company: string
  location: string | null
  job_url: string | null
  description: string
  extracted_requirements: any
}

interface Application {
  id: string
  job_id: string
  resume_id: string | null
  status: 'SAVED' | 'APPLIED' | 'INTERVIEWING' | 'OFFERED' | 'REJECTED'
  notes: string | null
  applied_at: string | null
  created_at: string
  job: Job
  workflow_status: string | null
}

interface Resume {
  id: string
  file_name: string
  file_path: string
  parsed_text: string | null
  parsed_json: any
  created_at: string
}

interface WorkExperienceItem {
  role: string
  company: string
  duration: string
  achievements: string[]
  source_text?: string
}

interface EducationItem {
  degree: string
  institution: string
  duration: string
  source_text?: string
}

interface ProjectItem {
  name: string
  description: string
  source_text?: string
}

interface ProfileData {
  name: string
  email: string
  phone: string
  location: string
  summary: string
  work_experience: WorkExperienceItem[]
  education: EducationItem[]
  skills: string[]
  tools: string[]
  projects: ProjectItem[]
  certifications: string[]
  achievements: string[]
  metrics: string[]
}

interface Profile {
  id: string
  user_id: string
  resume_id: string | null
  raw_text: string | null
  profile_json: ProfileData
  confirmed: boolean
  created_at: string
  updated_at: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<'applications' | 'jobs' | 'profile' | 'versions'>('applications')
  
  // Auth & Isolation States
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [isRegisterMode, setIsRegisterMode] = useState(false)
  
  // Telemetry Tracker
  const trackEvent = (eventName: string, properties: any = {}) => {
    console.log(`[Telemetry Event] ${eventName}:`, properties);
  }

  // Authenticated Fetch Wrapper
  const authFetch = async (url: string, options: RequestInit = {}) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const headers = {
      ...options.headers,
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
    return fetch(url, { ...options, headers });
  }

  const [applications, setApplications] = useState<Application[]>([])
  const [resumes, setResumes] = useState<Resume[]>([])
  const [selectedResumeId, setSelectedResumeId] = useState<string>('')
  const [profile, setProfile] = useState<Profile | null>(null)
  
  // Jobs Tab States
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJobId, setSelectedJobId] = useState<string>('')
  const [newJobTitle, setNewJobTitle] = useState('')
  const [newJobCompany, setNewJobCompany] = useState('')
  const [newJobLocation, setNewJobLocation] = useState('')
  const [newJobUrl, setNewJobUrl] = useState('')
  const [newJobDescription, setNewJobDescription] = useState('')
  
  // Profile editing state
  const [editingProfile, setEditingProfile] = useState<ProfileData | null>(null)
  
  // Form states (applications)
  const [newTitle, setNewTitle] = useState('')
  const [newCompany, setNewCompany] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [newStatus, setNewStatus] = useState<'SAVED' | 'APPLIED'>('SAVED')
  const [newNotes, setNewNotes] = useState('')
  
  // Selected analysis states
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [suggestionsResult, setSuggestionsResult] = useState<any>(null)

  // Feedback states
  const [feedbackRating, setFeedbackRating] = useState(5)
  const [feedbackComment, setFeedbackComment] = useState('')
  const [submittingFeedback, setSubmittingFeedback] = useState(false)
  const [activeAppId, setActiveAppId] = useState<string | null>(null)
  const [jobFitAnalysis, setJobFitAnalysis] = useState<any>(null)
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [resumeVersions, setResumeVersions] = useState<any[]>([])
  const [selectedVersionId, setSelectedVersionId] = useState<string>('')
  const [versionsJobId, setVersionsJobId] = useState<string>('')
  
  // UI states
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Toast notifications state
  const [notifications, setNotifications] = useState<{ id: string; message: string; type: 'success' | 'error' | 'info' | 'warning' }[]>([])

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info') => {
    const id = Math.random().toString(36).substring(2, 9)
    setNotifications(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id))
    }, 5000)
  }

  const removeToast = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  // Custom confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{ isOpen: boolean; message: string; onConfirm: () => void }>({
    isOpen: false,
    message: '',
    onConfirm: () => {}
  })

  const triggerConfirm = (message: string, onConfirm: () => void) => {
    setConfirmModal({
      isOpen: true,
      message,
      onConfirm: () => {
        onConfirm()
        setConfirmModal(prev => ({ ...prev, isOpen: false }))
      }
    })
  }

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authEmail || !authPassword) {
      showToast('Please enter both email and password.', 'error');
      return;
    }
    try {
      setActionLoading(true);
      if (isRegisterMode) {
        const res = await authFetch(`${API_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: authEmail, password: authPassword })
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || 'Registration failed');
        }
        showToast('Registration successful! Please log in.', 'success');
        setIsRegisterMode(false);
        setAuthPassword('');
      } else {
        const res = await authFetch(`${API_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: authEmail, password: authPassword })
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || 'Incorrect email or password.');
        }
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        setIsAuthenticated(true);
        showToast('Logged in successfully!', 'success');
        fetchData();
      }
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    showToast('Logged out.', 'success');
  };

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmittingFeedback(true);
      const res = await authFetch(`${API_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: feedbackRating, category: 'General', message: feedbackComment })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to submit feedback');
      }
      showToast('Thank you for your valuable feedback!', 'success');
      trackEvent('feedback_submitted', { rating: feedbackRating, comment_length: feedbackComment.length });
      setFeedbackComment('');
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const fetchResumeVersions = async () => {
    try {
      const res = await authFetch(`${API_URL}/resume-versions`)
      if (res.ok) {
        const data = await res.json()
        setResumeVersions(data)
      }
    } catch (err: any) {
      console.error('Failed to fetch resume versions:', err)
    }
  }

  // Fetch initial data
  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch applications
      const appsRes = await authFetch(`${API_URL}/applications`)
      if (!appsRes.ok) throw new Error('Failed to fetch applications')
      const appsData = await appsRes.json()
      setApplications(appsData)
      
      // Fetch resumes
      const resumesRes = await authFetch(`${API_URL}/resumes`)
      if (!resumesRes.ok) throw new Error('Failed to fetch resumes')
      const resumesData = await resumesRes.json()
      setResumes(resumesData)
      
      if (resumesData.length > 0) {
        setSelectedResumeId(resumesData[0].id)
      }
      
      // Fetch active profile
      const profileRes = await authFetch(`${API_URL}/profile`)
      if (profileRes.ok) {
        const profileData = await profileRes.json()
        setProfile(profileData)
        setEditingProfile(profileData.profile_json)
      }

      // Fetch saved jobs
      const jobsRes = await authFetch(`${API_URL}/jobs`)
      if (jobsRes.ok) {
        const jobsData = await jobsRes.json()
        setJobs(jobsData)
        if (jobsData.length > 0) {
          setSelectedJobId(jobsData[0].id)
        }
      }
      await fetchResumeVersions()
    } catch (err: any) {
      console.error(err)
      setError('Could not connect to backend services. Ensure the FastAPI server is running.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    setJobFitAnalysis(null)
    setSuggestions([])
    if (selectedJobId) {
      fetchSuggestions(selectedJobId)
    }
  }, [selectedJobId])

  // Handle Application Create
  const handleAddApplication = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle || !newCompany) return

    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/applications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle,
          company: newCompany,
          description: newDescription,
          status: newStatus,
          notes: newNotes,
          resume_id: selectedResumeId || null
        })
      })

      if (!res.ok) throw new Error('Failed to add application')
      
      setNewTitle('')
      setNewCompany('')
      setNewDescription('')
      setNewNotes('')
      await fetchData()
      showToast('Application added successfully!', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Job Create and Analysis
  const handleAddAndAnalyzeJob = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newJobTitle || !newJobCompany || !newJobDescription) {
      showToast('Please fill out Title, Company, and Description.', 'warning')
      return
    }

    try {
      setActionLoading(true)
      
      // 1. Create Job record
      const createRes = await authFetch(`${API_URL}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newJobTitle,
          company: newJobCompany,
          location: newJobLocation || null,
          job_url: newJobUrl || null,
          description: newJobDescription
        })
      })

      if (!createRes.ok) {
        const errData = await createRes.json()
        throw new Error(errData.detail || 'Failed to create job posting.')
      }
      
      const savedJob = await createRes.json()

      // 2. Trigger Job Parsing Analysis
      const analyzeRes = await authFetch(`${API_URL}/jobs/${savedJob.id}/analyze`, {
        method: 'POST'
      })

      if (!analyzeRes.ok) throw new Error('Job description saving succeeded, but requirements extraction failed.')
      
      showToast('Job record saved and requirements extracted!', 'success')
      
      // Reset Job form
      setNewJobTitle('')
      setNewJobCompany('')
      setNewJobLocation('')
      setNewJobUrl('')
      setNewJobDescription('')
      
      await fetchData()
      setSelectedJobId(savedJob.id)
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  // Delete Job Posting
  const handleDeleteJob = (jobId: string) => {
    triggerConfirm(
      'Are you sure you want to delete this job posting? This will delete all linked application trackers.',
      async () => {
        try {
          const res = await authFetch(`${API_URL}/jobs/${jobId}`, { method: 'DELETE' })
          if (!res.ok) throw new Error('Failed to delete job')
          if (selectedJobId === jobId) {
            setSelectedJobId('')
          }
          await fetchData()
          showToast('Job posting deleted successfully.', 'success')
        } catch (err: any) {
          showToast(err.message, 'error')
        }
      }
    )
  }

  // Ingested Job description requirements extraction
  const handleAnalyzeJob = async (jobId: string) => {
    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/jobs/${jobId}/analyze`, { method: 'POST' })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Job description requirements extraction failed.')
      }
      showToast('Job description analyzed and requirements extracted!', 'success')
      await fetchData()
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  // Deterministic fit analysis for a job posting
  const handleAnalyzeJobFit = async (jobId: string) => {
    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/analysis/fit-analysis?job_id=${jobId}`, { method: 'POST' })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Fit analysis failed')
      }
      const data = await res.json()
      setJobFitAnalysis(data)
      showToast('Fit analysis completed successfully!', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  const fetchSuggestions = async (jobId: string) => {
    try {
      const res = await authFetch(`${API_URL}/analysis/suggestions/${jobId}`)
      if (res.ok) {
        const data = await res.json()
        setSuggestions(data)
      }
    } catch (err: any) {
      console.error('Failed to fetch suggestions:', err)
    }
  }

  const handleGenerateSuggestions = async (jobId: string) => {
    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/analysis/suggestions?job_id=${jobId}`, { method: 'POST' })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Suggestions generation failed')
      }
      const data = await res.json()
      setSuggestions(data)
      showToast('Resume tailoring suggestions generated successfully!', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  const handleUpdateSuggestionStatus = async (sugId: string, newStatus: string) => {
    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/analysis/suggestions/${sugId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to update suggestion status')
      }
      const updated = await res.json()
      setSuggestions(prev => prev.map(s => s.id === sugId ? updated : s))
      showToast(`Suggestion status updated to ${newStatus}!`, 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  const handleEditSuggestionText = (sugId: string, newText: string) => {
    setSuggestions(prev => prev.map(s => {
      if (s.id === sugId) {
        return { ...s, suggested_text: newText, status: 'EDITED' }
      }
      return s
    }))
  }

  const handleSaveEditedSuggestion = async (sugId: string, editedText: string) => {
    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/analysis/suggestions/${sugId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suggested_text: editedText })
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to save suggestion edit')
      }
      const updated = await res.json()
      setSuggestions(prev => prev.map(s => s.id === sugId ? updated : s))
      showToast('Suggestion edit saved successfully!', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Status Toggle
  const handleUpdateStatus = async (appId: string, currentStatus: string) => {
    const nextStatusMap: Record<string, 'SAVED' | 'APPLIED' | 'INTERVIEWING' | 'OFFERED' | 'REJECTED'> = {
      SAVED: 'APPLIED',
      APPLIED: 'INTERVIEWING',
      INTERVIEWING: 'OFFERED',
      OFFERED: 'REJECTED',
      REJECTED: 'SAVED'
    }
    const nextStatus = nextStatusMap[currentStatus] || 'SAVED'

    try {
      const res = await authFetch(`${API_URL}/applications/${appId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus })
      })
      if (!res.ok) throw new Error('Failed to update status')
      await fetchData()
      showToast('Application status updated.', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    }
  }

  // Delete Application
  const handleDeleteApplication = (appId: string) => {
    triggerConfirm(
      'Are you sure you want to delete this application?',
      async () => {
        try {
          const res = await authFetch(`${API_URL}/applications/${appId}`, { method: 'DELETE' })
          if (!res.ok) throw new Error('Failed to delete application')
          if (activeAppId === appId) {
            setAnalysisResult(null)
            setSuggestionsResult(null)
            setActiveAppId(null)
          }
          await fetchData()
          showToast('Application deleted successfully.', 'success')
        } catch (err: any) {
          showToast(err.message, 'error')
        }
      }
    )
  }

  // Trigger Resume Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      setUploading(true)
      const res = await authFetch(`${API_URL}/resumes/upload`, {
        method: 'POST',
        body: formData
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Upload failed')
      }
      await fetchData()
      showToast('Resume uploaded and text extracted successfully!', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setUploading(false)
    }
  }

  // Trigger Parse Resume to Profile
  const handleParseResume = async (resumeId: string) => {
    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/resumes/${resumeId}/parse`, { method: 'POST' })
      if (!res.ok) throw new Error('Resume parsing failed')
      const data = await res.json()
      setProfile(data)
      setEditingProfile(data.profile_json)
      setActiveTab('profile')
      showToast('Deterministic section parsing completed. Redirected to Candidate Profile review tab.', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  // Edit profile local state functions
  const updateProfileField = (key: keyof ProfileData, value: any) => {
    if (!editingProfile) return
    setEditingProfile({
      ...editingProfile,
      [key]: value
    })
  }

  const updateExperienceField = (index: number, key: keyof WorkExperienceItem, value: any) => {
    if (!editingProfile) return
    const updated = [...editingProfile.work_experience]
    updated[index] = { ...updated[index], [key]: value }
    setEditingProfile({
      ...editingProfile,
      work_experience: updated
    })
  }

  const updateEducationField = (index: number, key: keyof EducationItem, value: any) => {
    if (!editingProfile) return
    const updated = [...editingProfile.education]
    updated[index] = { ...updated[index], [key]: value }
    setEditingProfile({
      ...editingProfile,
      education: updated
    })
  }

  // Save changes to backend
  const handleSaveProfile = async () => {
    if (!editingProfile) return
    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_json: editingProfile })
      })
      if (!res.ok) throw new Error('Failed to save profile changes')
      const data = await res.json()
      setProfile(data)
      setEditingProfile(data.profile_json)
      showToast('Profile saved successfully! Remember to confirm it once verified.', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  // Confirm candidate profile
  const handleConfirmProfile = async () => {
    try {
      setActionLoading(true)
      const res = await authFetch(`${API_URL}/profile/confirm`, { method: 'POST' })
      if (!res.ok) throw new Error('Failed to confirm profile')
      const data = await res.json()
      setProfile(data)
      setEditingProfile(data.profile_json)
      showToast('Candidate Profile Confirmed! This verified profile is now set as the only source of truth for AI tailoring.', 'success')
    } catch (err: any) {
      showToast(err.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  // Trigger Fit Analysis
  const runFitAnalysis = async (appId: string) => {
    try {
      setActionLoading(true)
      setActiveAppId(appId)
      
      const fitRes = await authFetch(`${API_URL}/analysis/fit-analysis?application_id=${appId}`, { method: 'POST' })
      if (!fitRes.ok) {
        const errorData = await fitRes.json()
        throw new Error(errorData.detail || 'Fit analysis failed')
      }
      const fitData = await fitRes.json()
      setAnalysisResult(fitData)

      const sugRes = await authFetch(`${API_URL}/analysis/suggestions?application_id=${appId}`, { method: 'POST' })
      if (!sugRes.ok) throw new Error('Suggestions fetch failed')
      const sugData = await sugRes.json()
      setSuggestionsResult(sugData)

    } catch (err: any) {
      showToast(err.message, 'error')
      setAnalysisResult(null)
      setSuggestionsResult(null)
      setActiveAppId(null)
    } finally {
      setActionLoading(false)
    }
  }

  const selectedJob = jobs.find(j => j.id === selectedJobId)

  if (!isAuthenticated && !loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#0a0a12', padding: '1.5rem' }}>
        <div className="card" style={{ width: '450px', padding: '2.5rem', background: '#161622', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.06)', boxShadow: '0 20px 50px rgba(0,0,0,0.4)' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h1 style={{ fontSize: '2rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.5px', margin: 0 }}>
              Job Application Copilot
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
              {isRegisterMode 
                ? 'Create a Private Beta account to get started' 
                : 'Sign in to access your truthful application suite'}
            </p>
          </div>

          <div style={{ background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '0.8rem 1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.8rem', color: 'var(--accent-primary)', display: 'flex', gap: '0.5rem' }}>
            <span>ℹ️</span>
            <span><strong>Private Beta</strong> — Please review all AI-generated content before using it.</span>
          </div>

          <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>Email Address</label>
              <input 
                type="email" 
                className="input" 
                placeholder="you@example.com" 
                value={authEmail} 
                onChange={(e) => setAuthEmail(e.target.value)} 
                required 
                disabled={actionLoading}
              />
            </div>
            
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>Password</label>
              <input 
                type="password" 
                className="input" 
                placeholder="••••••••" 
                value={authPassword} 
                onChange={(e) => setAuthPassword(e.target.value)} 
                required 
                disabled={actionLoading}
              />
            </div>

            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: '100%', justifyContent: 'center', padding: '0.75rem', marginTop: '0.5rem', fontWeight: 600 }}
              disabled={actionLoading}
            >
              {actionLoading 
                ? 'Processing...' 
                : (isRegisterMode ? '✨ Create Account' : '🔑 Sign In')}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            {isRegisterMode ? (
              <span>
                Already have an account?{' '}
                <button 
                  onClick={() => setIsRegisterMode(false)} 
                  style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', cursor: 'pointer', fontWeight: 600, padding: 0 }}
                >
                  Sign In
                </button>
              </span>
            ) : (
              <span>
                Don't have a Private Beta account?{' '}
                <button 
                  onClick={() => setIsRegisterMode(true)} 
                  style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', cursor: 'pointer', fontWeight: 600, padding: 0 }}
                >
                  Create Account
                </button>
              </span>
            )}
          </div>
          
          <div style={{ textAlign: 'center', marginTop: '2rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Default test account: <code>dev@example.com</code> / <code>password123</code>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Private Beta Top Banner */}
      <div style={{
        background: 'linear-gradient(90deg, #1d4ed8, #3b82f6)',
        color: '#fff',
        padding: '0.5rem 1rem',
        fontSize: '0.82rem',
        fontWeight: 600,
        textAlign: 'center',
        borderRadius: '8px',
        marginBottom: '1rem',
        boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)'
      }}>
        🚀 Private Beta — This product is under active development. Please review all AI-generated content before using it.
      </div>

      {/* Page Header */}
      <header style={{ padding: '1rem 0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 800, marginBottom: '0.5rem' }}>
            Job Application Copilot
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Tailor applications truthfully based on verified candidate profile evidence.
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button 
            className="btn btn-secondary"
            onClick={handleLogout}
            style={{ fontSize: '0.8rem', padding: '0.5rem 0.8rem' }}
          >
            🔑 Log Out
          </button>
        </div>
        
        {/* Navigation Tabs */}
        <div className="card" style={{ padding: '0.4rem', borderRadius: '12px', display: 'flex', gap: '0.2rem', background: '#161622', boxShadow: 'none' }}>
          <button 
            className={`btn ${activeTab === 'applications' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.5rem 1rem', borderRadius: '8px', fontSize: '0.9rem' }}
            onClick={() => { setActiveTab('applications'); setAnalysisResult(null); setSuggestionsResult(null); setActiveAppId(null); }}
          >
            📋 Application Tracker
          </button>
          <button 
            className={`btn ${activeTab === 'jobs' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.5rem 1rem', borderRadius: '8px', fontSize: '0.9rem' }}
            onClick={() => setActiveTab('jobs')}
          >
            💼 Jobs Intake & Parsing
          </button>
          <button 
            className={`btn ${activeTab === 'profile' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.5rem 1rem', borderRadius: '8px', fontSize: '0.9rem', position: 'relative' }}
            onClick={() => setActiveTab('profile')}
          >
            👤 Profile Confirmation
            {profile && !profile.confirmed && (
              <span style={{
                position: 'absolute',
                top: '-4px',
                right: '-4px',
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: 'var(--accent-warning)',
                boxShadow: '0 0 8px var(--accent-warning)'
              }} title="Unconfirmed Changes" />
            )}
          </button>
          <button 
            className={`btn ${activeTab === 'versions' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.5rem 1rem', borderRadius: '8px', fontSize: '0.9rem' }}
            onClick={() => setActiveTab('versions')}
          >
            📄 Tailored Resumes
          </button>
        </div>
      </header>

      {error && (
        <div className="card" style={{ borderLeft: '4px solid var(--accent-error)', marginBottom: '2rem' }}>
          <p style={{ color: 'var(--accent-error)', fontWeight: 600 }}>{error}</p>
          <button className="btn btn-secondary" style={{ marginTop: '0.8rem' }} onClick={fetchData}>
            Retry Connection
          </button>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '4rem 0', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🔄</div>
          <p>Connecting to database services and preparing dashboard...</p>
        </div>
      ) : (
        <>
          {/* Guided Onboarding Empty State */}
          {(resumes.length === 0 || !profile || !profile.confirmed) && (
            <div className="card" style={{ borderLeft: '4px solid var(--accent-primary)', marginBottom: '2rem', background: '#161622' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.8rem', color: '#fff' }}>
            🏁 Guided Onboarding: Build Your First Tailored Application
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.2rem', lineHeight: 1.5 }}>
            Welcome to the Private Beta! Follow these 6 steps to generate a truthfully tailored resume version for your target job:
          </p>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
            <div 
              onClick={() => setActiveTab('profile')}
              style={{
                padding: '0.8rem',
                borderRadius: '8px',
                background: resumes.length > 0 ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                border: resumes.length > 0 ? '1px solid var(--accent-success)' : '1px solid var(--border-color)',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '0.72rem', color: resumes.length > 0 ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                {resumes.length > 0 ? '✓ Step 1 Done' : 'Step 1'}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                📄 Upload Resume
              </div>
            </div>

            <div 
              onClick={() => setActiveTab('profile')}
              style={{
                padding: '0.8rem',
                borderRadius: '8px',
                background: (profile && profile.confirmed) ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                border: (profile && profile.confirmed) ? '1px solid var(--accent-success)' : '1px solid var(--border-color)',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '0.72rem', color: (profile && profile.confirmed) ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                {(profile && profile.confirmed) ? '✓ Step 2 Done' : 'Step 2'}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                👤 Confirm Profile
              </div>
            </div>

            <div 
              onClick={() => setActiveTab('jobs')}
              style={{
                padding: '0.8rem',
                borderRadius: '8px',
                background: jobs.length > 0 ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                border: jobs.length > 0 ? '1px solid var(--accent-success)' : '1px solid var(--border-color)',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '0.72rem', color: jobs.length > 0 ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                {jobs.length > 0 ? '✓ Step 3 Done' : 'Step 3'}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                💼 Add Job
              </div>
            </div>

            <div 
              onClick={() => setActiveTab('jobs')}
              style={{
                padding: '0.8rem',
                borderRadius: '8px',
                background: applications.some(a => a.workflow_status === 'RESUME_VERSION_ACTIVE' || a.workflow_status === 'RESUME_VERSION_CREATED' || a.workflow_status === 'SUGGESTIONS_REVIEWED') ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                border: applications.some(a => a.workflow_status === 'RESUME_VERSION_ACTIVE' || a.workflow_status === 'RESUME_VERSION_CREATED' || a.workflow_status === 'SUGGESTIONS_REVIEWED') ? '1px solid var(--accent-success)' : '1px solid var(--border-color)',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '0.72rem', color: applications.some(a => a.workflow_status === 'RESUME_VERSION_ACTIVE' || a.workflow_status === 'RESUME_VERSION_CREATED' || a.workflow_status === 'SUGGESTIONS_REVIEWED') ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                {applications.some(a => a.workflow_status === 'RESUME_VERSION_ACTIVE' || a.workflow_status === 'RESUME_VERSION_CREATED' || a.workflow_status === 'SUGGESTIONS_REVIEWED') ? '✓ Step 4 Done' : 'Step 4'}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                ⚡ Run Fit Analysis
              </div>
            </div>

            <div 
              onClick={() => setActiveTab('jobs')}
              style={{
                padding: '0.8rem',
                borderRadius: '8px',
                background: applications.some(a => a.workflow_status === 'RESUME_VERSION_ACTIVE' || a.workflow_status === 'RESUME_VERSION_CREATED') ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                border: applications.some(a => a.workflow_status === 'RESUME_VERSION_ACTIVE' || a.workflow_status === 'RESUME_VERSION_CREATED') ? '1px solid var(--accent-success)' : '1px solid var(--border-color)',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '0.72rem', color: applications.some(a => a.workflow_status === 'RESUME_VERSION_ACTIVE' || a.workflow_status === 'RESUME_VERSION_CREATED') ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                {applications.some(a => a.workflow_status === 'RESUME_VERSION_ACTIVE' || a.workflow_status === 'RESUME_VERSION_CREATED') ? '✓ Step 5 Done' : 'Step 5'}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                ✨ Review Suggestions
              </div>
            </div>

            <div 
              onClick={() => setActiveTab('versions')}
              style={{
                padding: '0.8rem',
                borderRadius: '8px',
                background: resumeVersions.length > 0 ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                border: resumeVersions.length > 0 ? '1px solid var(--accent-success)' : '1px solid var(--border-color)',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '0.72rem', color: resumeVersions.length > 0 ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                {resumeVersions.length > 0 ? '✓ Step 6 Done' : 'Step 6'}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                📄 Compose Version
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="dashboard-grid">
          
          {/* TAB 1: APPLICATIONS WORKSPACE */}
          {activeTab === 'applications' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Active Applications */}
              <div className="card">
                <h2 className="section-title">Tracked Applications</h2>
                {applications.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-muted)' }}>
                    <p>No job applications tracked yet. Use the form below to start tracking.</p>
                  </div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table className="app-table">
                      <thead>
                        <tr>
                          <th>Job Info</th>
                          <th>Status</th>
                          <th>Linked Resume</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {applications.map((app) => (
                          <tr key={app.id} style={{ background: activeAppId === app.id ? 'rgba(138, 43, 226, 0.05)' : '' }}>
                            <td>
                              <div style={{ fontWeight: 600, color: '#fff' }}>{app.job.title}</div>
                              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{app.job.company}</div>
                            </td>
                            <td>
                              <button
                                onClick={() => handleUpdateStatus(app.id, app.status)}
                                className={`badge badge-${app.status.toLowerCase()}`}
                                style={{ border: 'none', cursor: 'pointer' }}
                                title="Click to toggle status"
                              >
                                {app.status}
                              </button>
                            </td>
                            <td>
                              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                {app.resume_id ? '📄 Linked' : '❌ Unlinked'}
                              </span>
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button 
                                  className="btn btn-secondary" 
                                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                                  onClick={() => runFitAnalysis(app.id)}
                                >
                                  {activeAppId === app.id && actionLoading ? 'Analyzing...' : '⚡ Copilot'}
                                </button>
                                <button 
                                  className="btn btn-secondary" 
                                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', color: 'var(--accent-error)' }}
                                  onClick={() => handleDeleteApplication(app.id)}
                                >
                                  🗑️
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Add Application Form */}
              <div className="card">
                <h2 className="section-title">Add New Job Application</h2>
                <form onSubmit={handleAddApplication} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Job Title *
                      </label>
                      <input
                        type="text"
                        className="input"
                        placeholder="e.g. Software Engineer"
                        value={newTitle}
                        onChange={(e) => setNewTitle(e.target.value)}
                        required
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Company *
                      </label>
                      <input
                        type="text"
                        className="input"
                        placeholder="e.g. Acme Corp"
                        value={newCompany}
                        onChange={(e) => setNewCompany(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                      Job Description
                    </label>
                    <textarea
                      className="input"
                      placeholder="Paste job description here..."
                      rows={4}
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                      style={{ resize: 'vertical' }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Status
                      </label>
                      <select
                        className="input"
                        value={newStatus}
                        onChange={(e) => setNewStatus(e.target.value as any)}
                      >
                        <option value="SAVED">Saved</option>
                        <option value="APPLIED">Applied</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Linked Profile Resume
                      </label>
                      <select
                        className="input"
                        value={selectedResumeId}
                        onChange={(e) => setSelectedResumeId(e.target.value)}
                      >
                        <option value="">No Resume Linked</option>
                        {resumes.map(r => (
                          <option key={r.id} value={r.id}>{r.file_name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                      Notes
                    </label>
                    <input
                      type="text"
                      className="input"
                      placeholder="e.g. HR screen details..."
                      value={newNotes}
                      onChange={(e) => setNewNotes(e.target.value)}
                    />
                  </div>

                  <button 
                    type="submit" 
                    className="btn btn-primary" 
                    style={{ alignSelf: 'flex-start', marginTop: '0.5rem' }}
                    disabled={actionLoading}
                  >
                    {actionLoading ? 'Saving...' : '➕ Track Application'}
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* TAB 2: JOBS INTAKE & PARSING */}
          {activeTab === 'jobs' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              
              {/* Saved Jobs List */}
              <div className="card">
                <h2 className="section-title">Ingested Job Postings</h2>
                {jobs.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-muted)' }}>
                    <p>No job descriptions ingested yet. Use the form below to parse one.</p>
                  </div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table className="app-table">
                      <thead>
                        <tr>
                          <th>Job Listing</th>
                          <th>Location</th>
                          <th>Requirements Parse</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map((job) => (
                          <tr key={job.id} style={{ background: selectedJobId === job.id ? 'rgba(138, 43, 226, 0.05)' : '' }}>
                            <td>
                              <div style={{ fontWeight: 600, color: '#fff' }}>{job.title}</div>
                              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{job.company}</div>
                            </td>
                            <td>
                              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                {job.location || 'Not Specified'}
                              </span>
                            </td>
                            <td>
                              <span className={`badge ${job.extracted_requirements ? 'badge-offered' : 'badge-saved'}`}>
                                {job.extracted_requirements ? '✓ Extracted' : 'Pending'}
                              </span>
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button 
                                  className="btn btn-secondary" 
                                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                                  onClick={() => setSelectedJobId(job.id)}
                                >
                                  👁️ View
                                </button>
                                <button 
                                  className="btn btn-secondary" 
                                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', color: 'var(--accent-error)' }}
                                  onClick={() => handleDeleteJob(job.id)}
                                >
                                  🗑️
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* AI Resume Tailoring Suggestions Review Workspace */}
              {selectedJob && suggestions && suggestions.length > 0 && (
                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', border: '1px solid rgba(218, 165, 32, 0.3)', background: 'rgba(20, 20, 20, 0.4)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h2 className="section-title" style={{ margin: 0 }}>✨ AI Resume Tailoring Suggestions</h2>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                        Review, edit, and approve tailoring suggestions for <strong>{selectedJob.title}</strong>.
                      </p>
                    </div>
                    <span className="badge badge-interviewing" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
                      {suggestions.filter(s => s.status === 'APPROVED').length} / {suggestions.length} Approved
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                    {suggestions.map((sug) => (
                      <div key={sug.id} style={{ 
                        background: 'rgba(255, 255, 255, 0.02)', 
                        border: `1px solid ${
                          sug.status === 'APPROVED' ? 'rgba(16, 185, 129, 0.3)' : 
                          sug.status === 'REJECTED' ? 'rgba(239, 68, 68, 0.3)' : 
                          sug.status === 'EDITED' ? 'rgba(138, 43, 226, 0.3)' : 
                          'var(--border-color)'
                        }`, 
                        borderRadius: '10px', 
                        padding: '1.2rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.8rem'
                      }}>
                        {/* Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                          <div>
                            <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--accent-secondary)', textTransform: 'uppercase' }}>
                              {sug.suggestion_type}
                            </span>
                            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: '0.1rem 0 0 0', color: '#fff' }}>Section: {sug.section}</h3>
                          </div>
                          
                          <span className={`badge badge-${
                            sug.status === 'APPROVED' ? 'offered' : 
                            sug.status === 'REJECTED' ? 'rejected' : 
                            sug.status === 'EDITED' ? 'interviewing' : 
                            'saved'
                          }`}>
                            {sug.status}
                          </span>
                        </div>

                        {/* Text Diff Grid */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '0.2rem' }}>
                          {/* Original Text */}
                          <div style={{ background: 'rgba(239, 68, 68, 0.03)', padding: '0.8rem', borderRadius: '8px', borderLeft: '3px solid var(--accent-error)' }}>
                            <div style={{ fontSize: '0.72rem', color: 'var(--accent-error)', fontWeight: 600, marginBottom: '0.4rem', textTransform: 'uppercase' }}>Original Text</div>
                            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, whiteSpace: 'pre-wrap' }}>
                              {sug.original_text || <em>(Empty section/addition suggestion)</em>}
                            </p>
                          </div>

                          {/* Suggested Text (Editable Text Area) */}
                          <div style={{ background: 'rgba(16, 185, 129, 0.03)', padding: '0.8rem', borderRadius: '8px', borderLeft: '3px solid var(--accent-success)' }}>
                            <div style={{ fontSize: '0.72rem', color: 'var(--accent-success)', fontWeight: 600, marginBottom: '0.4rem', textTransform: 'uppercase' }}>Suggested Text (Editable)</div>
                            <textarea
                              value={sug.suggested_text}
                              onChange={(e) => handleEditSuggestionText(sug.id, e.target.value)}
                              style={{ 
                                width: '100%', 
                                background: 'rgba(0,0,0,0.3)', 
                                border: '1px solid var(--border-color)', 
                                borderRadius: '6px', 
                                color: '#fff', 
                                fontSize: '0.82rem', 
                                padding: '0.5rem', 
                                minHeight: '65px',
                                fontFamily: 'inherit',
                                resize: 'vertical'
                              }}
                            />
                          </div>
                        </div>

                        {/* Rationale & Evidence Grid */}
                        <div style={{ 
                          display: 'grid', 
                          gridTemplateColumns: '3fr 2fr', 
                          gap: '1.2rem', 
                          fontSize: '0.78rem', 
                          color: 'var(--text-secondary)', 
                          background: 'rgba(255,255,255,0.01)', 
                          padding: '0.8rem', 
                          borderRadius: '8px',
                          border: '1px solid var(--border-color)'
                        }}>
                          <div>
                            <div style={{ marginBottom: '0.3rem' }}><strong>🎯 Target Requirement:</strong> {sug.target_requirement}</div>
                            <div style={{ marginBottom: '0.3rem' }}><strong>💡 Rationale:</strong> {sug.rationale}</div>
                            <div>
                              <strong>🔍 Evidence:</strong> <span style={{ color: 'var(--accent-secondary)', fontStyle: 'italic' }}>"{sug.evidence}"</span>
                            </div>
                          </div>
                          
                          <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '1.2rem', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '0.3rem' }}>
                            <div>
                              <strong>Evidence Status:</strong> 
                              <span style={{ 
                                color: sug.evidence_status === 'SUPPORTED' ? 'var(--accent-success)' : 
                                       sug.evidence_status === 'REQUIRES_USER_CONFIRMATION' ? 'var(--accent-warning)' : 
                                       'var(--accent-error)',
                                marginLeft: '0.4rem',
                                fontWeight: 600
                              }}>
                                {sug.evidence_status}
                              </span>
                            </div>
                            <div>
                              <strong>Confidence:</strong> 
                              <span style={{ fontWeight: 600, color: '#fff', marginLeft: '0.4rem' }}>
                                {(sug.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Action buttons */}
                        <div style={{ display: 'flex', gap: '0.6rem', alignSelf: 'flex-end', marginTop: '0.4rem' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.4rem 1rem', fontSize: '0.78rem', borderColor: 'var(--accent-error)', color: 'var(--accent-error)', background: 'rgba(239, 68, 68, 0.05)' }}
                            onClick={() => handleUpdateSuggestionStatus(sug.id, 'REJECTED')}
                            disabled={actionLoading}
                          >
                            ✗ Reject
                          </button>
                          
                          {sug.status === 'EDITED' && (
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '0.4rem 1rem', fontSize: '0.78rem', borderColor: 'var(--accent-secondary)', color: 'var(--accent-secondary)', background: 'rgba(138, 43, 226, 0.05)' }}
                              onClick={() => handleSaveEditedSuggestion(sug.id, sug.suggested_text)}
                              disabled={actionLoading}
                            >
                              💾 Save Edit
                            </button>
                          )}

                          <button
                            className="btn btn-primary"
                            style={{ padding: '0.4rem 1rem', fontSize: '0.78rem' }}
                            onClick={() => handleUpdateSuggestionStatus(sug.id, 'APPROVED')}
                            disabled={actionLoading}
                          >
                            ✓ Approve
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Direct Compose CTA button */}
                  {suggestions.some(s => s.status === 'APPROVED' || s.status === 'EDITED') && (
                    <div style={{
                      marginTop: '1rem',
                      padding: '1.2rem',
                      background: 'rgba(59, 130, 246, 0.05)',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                      borderRadius: '10px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '1rem'
                    }}>
                      <div>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                          Ready to compose tailored resume?
                        </h4>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.1rem 0 0 0' }}>
                          You have {suggestions.filter(s => s.status === 'APPROVED' || s.status === 'EDITED').length} approved/edited suggestions.
                        </p>
                      </div>
                      <button
                        className="btn btn-primary"
                        style={{ padding: '0.6rem 1.2rem', fontSize: '0.85rem' }}
                        disabled={actionLoading}
                        onClick={async () => {
                          try {
                            setActionLoading(true);
                            const res = await authFetch(`${API_URL}/resume-versions`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ job_id: selectedJob.id })
                            });
                            if (!res.ok) {
                              const data = await res.json();
                              throw new Error(data.detail || 'Failed to compose resume version');
                            }
                            const data = await res.json();
                            showToast('Resume version composed successfully! Switched to Tailored Resumes workspace.', 'success');
                            trackEvent('resume_version_created', { version_id: data.id, job_id: selectedJob.id });
                            setResumeVersions(prev => [data, ...prev]);
                            setSelectedVersionId(data.id);
                            // Switch tab to versions
                            setActiveTab('versions');
                          } catch (err: any) {
                            showToast(err.message, 'error');
                          } finally {
                            setActionLoading(false);
                          }
                        }}
                      >
                        ⚙️ Compose Tailored Resume
                      </button>
                    </div>
                  )}

                </div>
              )}

              {/* Job Intake Form */}
              <div className="card">
                <h2 className="section-title">Ingest & Analyze New Job Description</h2>
                <form onSubmit={handleAddAndAnalyzeJob} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Role Title *
                      </label>
                      <input
                        type="text"
                        className="input"
                        placeholder="e.g. Senior Frontend Developer"
                        value={newJobTitle}
                        onChange={(e) => setNewJobTitle(e.target.value)}
                        required
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Company Name *
                      </label>
                      <input
                        type="text"
                        className="input"
                        placeholder="e.g. InnovateTech Corp"
                        value={newJobCompany}
                        onChange={(e) => setNewJobCompany(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Location
                      </label>
                      <input
                        type="text"
                        className="input"
                        placeholder="e.g. Remote / New York, NY"
                        value={newJobLocation}
                        onChange={(e) => setNewJobLocation(e.target.value)}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Job Posting URL
                      </label>
                      <input
                        type="url"
                        className="input"
                        placeholder="e.g. https://linkedin.com/jobs/..."
                        value={newJobUrl}
                        onChange={(e) => setNewJobUrl(e.target.value)}
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                      Raw Job Description Text *
                    </label>
                    <textarea
                      className="input"
                      placeholder="Paste the full job description text here..."
                      rows={6}
                      value={newJobDescription}
                      onChange={(e) => setNewJobDescription(e.target.value)}
                      style={{ resize: 'vertical' }}
                      required
                    />
                  </div>

                  <button 
                    type="submit" 
                    className="btn btn-primary" 
                    style={{ alignSelf: 'flex-start', marginTop: '0.5rem' }}
                    disabled={actionLoading}
                  >
                    {actionLoading ? 'Analyzing...' : '⚙️ Save & Analyze Job'}
                  </button>
                </form>
              </div>

            </div>
          )}

          {/* TAB 3: PROFILE CONFIRMATION & REVIEW WORKSPACE */}
          {activeTab === 'profile' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              
              {/* Profile Header Status Card */}
              <div className="card" style={{ borderLeft: profile?.confirmed ? '4px solid var(--accent-success)' : '4px solid var(--accent-warning)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                      Profile Verification Status
                    </h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                      {profile?.confirmed 
                        ? '✓ Verified. The fields below are confirmed as the single source of truth for future AI tailor evaluations.'
                        : '⚠️ Unconfirmed. Please review, edit, and click "Confirm Profile" below to activate AI suggestion guardrails.'
                      }
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button 
                      className="btn btn-secondary" 
                      onClick={handleSaveProfile}
                      disabled={actionLoading || !editingProfile}
                    >
                      💾 Save Changes
                    </button>
                    <button 
                      className={`btn ${profile?.confirmed ? 'btn-secondary' : 'btn-primary'}`} 
                      onClick={handleConfirmProfile}
                      disabled={actionLoading || !profile}
                      style={{ background: !profile?.confirmed ? 'linear-gradient(135deg, var(--accent-success) 0%, #059669 100%)' : '', boxShadow: !profile?.confirmed ? '0 4px 15px rgba(16, 185, 129, 0.4)' : '' }}
                    >
                      {profile?.confirmed ? '✓ Profile Confirmed' : '🛡️ Confirm Profile'}
                    </button>
                  </div>
                </div>
              </div>

              {editingProfile ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  
                  {/* Contact details */}
                  <div className="card">
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>Candidate Contact Details</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.2rem' }}>Name</label>
                        <input 
                          type="text" 
                          className="input" 
                          value={editingProfile.name || ''} 
                          onChange={(e) => updateProfileField('name', e.target.value)} 
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.2rem' }}>Email</label>
                        <input 
                          type="email" 
                          className="input" 
                          value={editingProfile.email || ''} 
                          onChange={(e) => updateProfileField('email', e.target.value)} 
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.2rem' }}>Phone</label>
                        <input 
                          type="text" 
                          className="input" 
                          value={editingProfile.phone || ''} 
                          onChange={(e) => updateProfileField('phone', e.target.value)} 
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.2rem' }}>Location</label>
                        <input 
                          type="text" 
                          className="input" 
                          value={editingProfile.location || ''} 
                          onChange={(e) => updateProfileField('location', e.target.value)} 
                        />
                      </div>
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="card">
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>Professional Summary</h3>
                    <textarea 
                      className="input" 
                      rows={4}
                      value={editingProfile.summary || ''} 
                      onChange={(e) => updateProfileField('summary', e.target.value)} 
                    />
                  </div>

                  {/* Experience Card */}
                  <div className="card">
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>Work Experience</h3>
                    {editingProfile.work_experience.length === 0 ? (
                      <p style={{ color: 'var(--text-muted)' }}>No experience items parsed.</p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        {editingProfile.work_experience.map((exp, idx) => (
                          <div key={idx} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1.5rem' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '0.8rem' }}>
                              <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Role</label>
                                <input 
                                  type="text" 
                                  className="input" 
                                  value={exp.role} 
                                  onChange={(e) => updateExperienceField(idx, 'role', e.target.value)}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Company</label>
                                <input 
                                  type="text" 
                                  className="input" 
                                  value={exp.company} 
                                  onChange={(e) => updateExperienceField(idx, 'company', e.target.value)}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Duration</label>
                                <input 
                                  type="text" 
                                  className="input" 
                                  value={exp.duration} 
                                  onChange={(e) => updateExperienceField(idx, 'duration', e.target.value)}
                                />
                              </div>
                            </div>
                            <div>
                              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Key Achievements (bullet points, comma separated)</label>
                              <textarea 
                                className="input" 
                                rows={3} 
                                value={exp.achievements.join("\n")} 
                                onChange={(e) => updateExperienceField(idx, 'achievements', e.target.value.split("\n"))}
                              />
                            </div>
                            {exp.source_text && (
                              <div style={{ marginTop: '0.6rem', fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.01)', padding: '0.5rem', borderRadius: '4px', borderLeft: '2px solid var(--accent-primary)' }}>
                                <strong>Original Text Match:</strong> {exp.source_text}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Education Card */}
                  <div className="card">
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>Education</h3>
                    {editingProfile.education.length === 0 ? (
                      <p style={{ color: 'var(--text-muted)' }}>No education items parsed.</p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        {editingProfile.education.map((edu, idx) => (
                          <div key={idx} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1.5rem' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                              <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Degree</label>
                                <input 
                                  type="text" 
                                  className="input" 
                                  value={edu.degree} 
                                  onChange={(e) => updateEducationField(idx, 'degree', e.target.value)}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Institution</label>
                                <input 
                                  type="text" 
                                  className="input" 
                                  value={edu.institution} 
                                  onChange={(e) => updateEducationField(idx, 'institution', e.target.value)}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Date</label>
                                <input 
                                  type="text" 
                                  className="input" 
                                  value={edu.duration} 
                                  onChange={(e) => updateEducationField(idx, 'duration', e.target.value)}
                                />
                              </div>
                            </div>
                            {edu.source_text && (
                              <div style={{ marginTop: '0.6rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                <strong>Source text:</strong> {edu.source_text}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Skills, Tools, Certifications */}
                  <div className="card">
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>Skills, Tools, Certs</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Skills (comma separated)</label>
                        <input 
                          type="text" 
                          className="input" 
                          value={editingProfile.skills.join(", ")} 
                          onChange={(e) => updateProfileField('skills', e.target.value.split(",").map((s: string) => s.trim()))} 
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Tools (comma separated)</label>
                        <input 
                          type="text" 
                          className="input" 
                          value={editingProfile.tools.join(", ")} 
                          onChange={(e) => updateProfileField('tools', e.target.value.split(",").map((s: string) => s.trim()))} 
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Certifications (comma separated)</label>
                        <input 
                          type="text" 
                          className="input" 
                          value={editingProfile.certifications.join(", ")} 
                          onChange={(e) => updateProfileField('certifications', e.target.value.split(",").map((s: string) => s.trim()))} 
                        />
                      </div>
                    </div>
                  </div>

                  {/* Achievements and metrics */}
                  <div className="card">
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>Achievements & Metrics</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Achievements (comma separated)</label>
                        <input 
                          type="text" 
                          className="input" 
                          value={editingProfile.achievements.join(", ")} 
                          onChange={(e) => updateProfileField('achievements', e.target.value.split(",").map((s: string) => s.trim()))} 
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Performance Metrics (comma separated)</label>
                        <input 
                          type="text" 
                          className="input" 
                          value={editingProfile.metrics.join(", ")} 
                          onChange={(e) => updateProfileField('metrics', e.target.value.split(",").map((s: string) => s.trim()))} 
                        />
                      </div>
                    </div>
                  </div>

                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-secondary)' }} className="card">
                  <p>No active candidate profile. Upload a resume and parse it to initialize your profile details.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'versions' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Selected Resume Version Details */}
              {(() => {
                const selectedVersion = resumeVersions.find(v => v.id === selectedVersionId);
                if (!selectedVersion) {
                  return (
                    <div className="card" style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-secondary)' }}>
                      <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>No Tailored Resume Versions</p>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                        Go to the <strong>Jobs Intake & Parsing</strong> tab, select a job, approve suggestions, and click <strong>Generate Suggestions</strong> and <strong>Compose Tailored Resume</strong> to create a versioned tailored resume.
                      </p>
                    </div>
                  );
                }

                const linkedJob = jobs.find(j => j.id === selectedVersion.job_id);
                const traceability = selectedVersion.content_json._traceability || {};

                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    
                    {/* Version Header Card */}
                    <div className="card" style={{ 
                      borderLeft: selectedVersion.status === 'ACTIVE' ? '4px solid var(--accent-success)' : '4px solid var(--border-hover)',
                      background: 'rgba(255, 255, 255, 0.01)'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-secondary)', textTransform: 'uppercase' }}>
                              Tailored Version
                            </span>
                            <span className={`badge badge-${
                              selectedVersion.status === 'ACTIVE' ? 'offered' : 
                              selectedVersion.status === 'INACTIVE' ? 'rejected' : 
                              'saved'
                            }`} style={{ fontSize: '0.7rem' }}>
                              {selectedVersion.status}
                            </span>
                          </div>
                          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '0.2rem', color: '#fff' }}>
                            {linkedJob ? linkedJob.title : 'Target Position'}
                          </h2>
                          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.1rem' }}>
                            🏢 {linkedJob ? linkedJob.company : 'Company'} | 📅 Generated: {new Date(selectedVersion.created_at).toLocaleString()}
                          </p>
                        </div>

                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.4rem 1rem', fontSize: '0.8rem' }}
                            onClick={() => {
                              navigator.clipboard.writeText(selectedVersion.content_markdown);
                              showToast('Tailored resume copied to clipboard!', 'success');
                              trackEvent('resume_downloaded', { version_id: selectedVersion.id, method: 'copy_clipboard' });
                            }}
                          >
                            📋 Copy Markdown
                          </button>

                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.4rem 1rem', fontSize: '0.8rem' }}
                            onClick={() => {
                              const blob = new Blob([selectedVersion.content_markdown], { type: 'text/markdown' });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = `tailored_resume_${linkedJob ? linkedJob.company.toLowerCase().replace(/\s+/g, '_') : 'version'}.md`;
                              document.body.appendChild(a);
                              a.click();
                              document.body.removeChild(a);
                              URL.revokeObjectURL(url);
                              showToast('Markdown resume downloaded!', 'success');
                              trackEvent('resume_downloaded', { version_id: selectedVersion.id, method: 'download_file' });
                            }}
                          >
                            📥 Download Markdown
                          </button>

                          <button
                            className="btn btn-secondary"
                            style={{ 
                              padding: '0.4rem 1rem', 
                              fontSize: '0.8rem',
                              borderColor: 'var(--accent-error)',
                              color: 'var(--accent-error)',
                              background: 'rgba(239, 68, 68, 0.05)'
                            }}
                            onClick={() => {
                              triggerConfirm('Are you sure you want to discard/delete this resume version?', async () => {
                                try {
                                  setActionLoading(true);
                                  const res = await authFetch(`${API_URL}/resume-versions/${selectedVersion.id}`, { method: 'DELETE' });
                                  if (!res.ok) throw new Error('Failed to delete version');
                                  showToast('Resume version discarded.', 'success');
                                  setSelectedVersionId('');
                                  await fetchResumeVersions();
                                } catch (err: any) {
                                  showToast(err.message, 'error');
                                } finally {
                                  setActionLoading(false);
                                }
                              });
                            }}
                            disabled={actionLoading}
                          >
                            🗑️ Discard Version
                          </button>

                          {selectedVersion.status !== 'ACTIVE' && (
                            <button
                              className="btn btn-primary"
                              style={{ padding: '0.4rem 1rem', fontSize: '0.8rem' }}
                              onClick={async () => {
                                try {
                                  setActionLoading(true);
                                  const res = await authFetch(`${API_URL}/resume-versions/${selectedVersion.id}/activate`, { method: 'POST' });
                                  if (!res.ok) throw new Error('Failed to activate version');
                                  showToast('Resume version activated successfully!', 'success');
                                  await fetchResumeVersions();
                                } catch (err: any) {
                                  showToast(err.message, 'error');
                                } finally {
                                  setActionLoading(false);
                                }
                              }}
                              disabled={actionLoading}
                            >
                              ✓ Accept & Activate
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Diff Review Card */}
                    <div className="card">
                      <h3 className="section-title">Resume Customization Comparison (Bullet-Level Diff)</h3>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1.2rem' }}>
                        Review custom sections modified by approved tailoring suggestions below.
                      </p>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        {/* Summary Section Diff */}
                        {(() => {
                          const isModified = Object.values(traceability).some((t: any) => t.section === 'Summary' || t.section === 'Summary / Skills');
                          const appliedSug: any = Object.values(traceability).find((t: any) => t.section === 'Summary' || t.section === 'Summary / Skills');
                          
                          return (
                            <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1.2rem' }}>
                              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-secondary)', marginBottom: '0.5rem' }}>
                                Section: Professional Summary
                              </h4>
                              {isModified && appliedSug ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                                  <div style={{ background: 'rgba(239, 68, 68, 0.12)', padding: '0.8rem', borderRadius: '6px', borderLeft: '4px solid #ef4444', fontSize: '0.82rem', textDecoration: 'line-through', color: '#fca5a5' }}>
                                    {appliedSug.original_text}
                                  </div>
                                  <div style={{ background: 'rgba(16, 185, 129, 0.12)', padding: '0.8rem', borderRadius: '6px', borderLeft: '4px solid #10b981', fontSize: '0.82rem', color: '#a7f3d0' }}>
                                    {appliedSug.suggested_text}
                                  </div>
                                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                    <strong>💡 Rationale:</strong> {appliedSug.evidence ? `Supported by profile evidence: "${appliedSug.evidence}"` : 'No explicit evidence provided.'}
                                  </div>
                                </div>
                              ) : (
                                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, fontStyle: 'italic' }}>
                                  Unchanged: "{selectedVersion.content_json.summary || '(Empty)'}"
                                </p>
                              )}
                            </div>
                          );
                        })()}

                        {/* Experience Section Diff */}
                        <div>
                          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-secondary)', marginBottom: '0.8rem' }}>
                            Section: Work Experience Bullet Points
                          </h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                            {selectedVersion.content_json.work_experience.map((exp: any, expIdx: number) => {
                              const originalExp = profile?.profile_json.work_experience.find(orig => orig.company === exp.company && orig.role === exp.role);
                              
                              return (
                                <div key={expIdx} style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem' }}>
                                  <h5 style={{ fontSize: '0.88rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                                    {exp.role} at <strong>{exp.company}</strong>
                                  </h5>
                                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.1rem 0 0.8rem 0' }}>{exp.duration}</p>
                                  
                                  <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', paddingLeft: '0.5rem', listStyle: 'none', margin: 0 }}>
                                    {exp.achievements.map((ach: string, achIdx: number) => {
                                      // Find if this achievement is modified (its text was replaced)
                                      const matchedSug: any = Object.values(traceability).find((t: any) => t.suggested_text === ach);
                                      
                                      if (matchedSug) {
                                        return (
                                          <li key={achIdx} style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', borderLeft: '2px dashed rgba(218, 165, 32, 0.4)', paddingLeft: '0.8rem' }}>
                                            <div style={{ background: 'rgba(239, 68, 68, 0.12)', padding: '0.5rem 0.7rem', borderRadius: '4px', borderLeft: '4px solid #ef4444', fontSize: '0.8rem', textDecoration: 'line-through', color: '#fca5a5' }}>
                                              {matchedSug.original_text}
                                            </div>
                                            <div style={{ background: 'rgba(16, 185, 129, 0.12)', padding: '0.5rem 0.7rem', borderRadius: '4px', borderLeft: '4px solid #10b981', fontSize: '0.8rem', color: '#a7f3d0' }}>
                                              {matchedSug.suggested_text}
                                            </div>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                              <strong>🔍 Evidence Trace:</strong> {matchedSug.evidence}
                                            </div>
                                          </li>
                                        );
                                      } else {
                                        return (
                                          <li key={achIdx} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', gap: '0.4rem', alignItems: 'flex-start' }}>
                                            <span style={{ color: 'var(--text-muted)' }}>•</span>
                                            <span>{ach}</span>
                                          </li>
                                        );
                                      }
                                    })}
                                  </ul>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {/* Skills and Tools Diff */}
                        {(() => {
                          const isSkillsModified = Object.values(traceability).some((t: any) => t.section === 'Skills & Tools');
                          const appliedSug: any = Object.values(traceability).find((t: any) => t.section === 'Skills & Tools');
                          
                          return (
                            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1.2rem' }}>
                              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-secondary)', marginBottom: '0.5rem' }}>
                                Section: Skills & Tools
                              </h4>
                              {isSkillsModified && appliedSug ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                                  <div style={{ background: 'rgba(239, 68, 68, 0.12)', padding: '0.6rem 0.8rem', borderRadius: '6px', borderLeft: '4px solid #ef4444', fontSize: '0.8rem', textDecoration: 'line-through', color: '#fca5a5' }}>
                                    {appliedSug.original_text}
                                  </div>
                                  <div style={{ background: 'rgba(16, 185, 129, 0.12)', padding: '0.6rem 0.8rem', borderRadius: '6px', borderLeft: '4px solid #10b981', fontSize: '0.8rem', color: '#a7f3d0' }}>
                                    {appliedSug.suggested_text}
                                  </div>
                                </div>
                              ) : (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                  {selectedVersion.content_json.skills.map((s: string) => (
                                    <span key={s} className="badge badge-applied" style={{ fontSize: '0.72rem' }}>{s}</span>
                                  ))}
                                  {selectedVersion.content_json.tools.map((t: string) => (
                                    <span key={t} className="badge badge-saved" style={{ fontSize: '0.72rem', borderColor: 'var(--accent-secondary)', color: 'var(--accent-secondary)' }}>{t}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })()}
                      </div>
                    </div>

                    {/* Markdown Source Preview */}
                    <div className="card">
                      <h3 className="section-title">Compiled Resume Markdown Source</h3>
                      <textarea
                        readOnly
                        value={selectedVersion.content_markdown}
                        style={{
                          width: '100%',
                          minHeight: '250px',
                          background: '#0d0d16',
                          border: '1px solid var(--border-color)',
                          borderRadius: '6px',
                          fontFamily: 'monospace',
                          color: '#a5a5b1',
                          fontSize: '0.8rem',
                          padding: '0.8rem',
                          resize: 'vertical'
                        }}
                      />
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* RIGHT SIDEBAR: DYNAMIC SIDEBAR UPDATING ACCORDING TO TABS */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            
            {/* SIDEBAR FOR APPLICATION TRACKER */}
            {activeTab === 'applications' && (
              <>
                {/* Resume Upload Panel */}
                <div className="card">
                  <h2 className="section-title">Manage Resumes</h2>
                  <div style={{ marginTop: '1rem' }}>
                    <label className="btn btn-secondary" style={{ display: 'flex', justifyContent: 'center', cursor: 'pointer', borderStyle: 'dashed' }}>
                      {uploading ? '📤 Uploading...' : '📄 Upload Resume (.txt, .md, .pdf, .docx)'}
                      <input type="file" onChange={handleFileUpload} accept=".txt,.md,.pdf,.docx" style={{ display: 'none' }} disabled={uploading} />
                    </label>
                  </div>
                  {resumes.length > 0 ? (
                    <div style={{ marginTop: '1.5rem' }}>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                        Select Uploaded Resume:
                      </label>
                      <select className="input" value={selectedResumeId} onChange={(e) => setSelectedResumeId(e.target.value)}>
                        {resumes.map(r => (
                          <option key={r.id} value={r.id}>{r.file_name}</option>
                        ))}
                      </select>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.8rem' }}>
                        <button className="btn btn-primary" style={{ flex: 1, padding: '0.5rem', fontSize: '0.85rem', justifyContent: 'center' }} onClick={() => handleParseResume(selectedResumeId)} disabled={actionLoading}>
                          ⚙️ Parse to Profile
                        </button>
                      </div>
                      {profile && (
                        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                            <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Candidate Profile:</span>
                            <span className={`badge ${profile.confirmed ? 'badge-offered' : 'badge-rejected'}`} style={{ fontSize: '0.65rem' }}>
                              {profile.confirmed ? 'Confirmed' : 'Unconfirmed'}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>👤 {profile.profile_json.name || 'No Name'}</div>
                          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>✉️ {profile.profile_json.email || 'No Email'}</div>
                          <button className="btn btn-secondary" style={{ width: '100%', fontSize: '0.8rem', justifyContent: 'center', padding: '0.4rem', marginTop: '0.6rem' }} onClick={() => { setEditingProfile(profile.profile_json); setActiveTab('profile'); }}>
                            ✏️ Review & Edit Profile
                          </button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '1rem', textAlign: 'center' }}>No resumes uploaded yet.</p>
                  )}
                </div>

                {/* Copilot Workings */}
                {analysisResult && (
                  <div className="card" style={{ borderLeft: '4px solid var(--accent-primary)' }}>
                    <h2 className="section-title">Fit Analysis</h2>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '1rem 0' }}>
                      <div style={{ 
                        width: '64px', 
                        height: '64px', 
                        borderRadius: '50%', 
                        background: analysisResult.match_score >= 80 ? 'rgba(16, 185, 129, 0.15)' : analysisResult.match_score >= 50 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)', 
                        border: `2px solid ${analysisResult.match_score >= 80 ? 'var(--accent-success)' : analysisResult.match_score >= 50 ? 'var(--accent-warning)' : 'var(--accent-error)'}`, 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center', 
                        fontSize: '1.3rem', 
                        fontWeight: 'bold', 
                        color: analysisResult.match_score >= 80 ? 'var(--accent-success)' : analysisResult.match_score >= 50 ? 'var(--accent-warning)' : 'var(--accent-error)' 
                      }}>
                        {analysisResult.match_score}%
                      </div>
                      <div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Recommendation</div>
                        <span className={`badge badge-${analysisResult.recommendation === 'APPLY' ? 'offered' : analysisResult.recommendation === 'CONSIDER' ? 'interviewing' : 'rejected'}`}>
                          {analysisResult.recommendation}
                        </span>
                      </div>
                    </div>
                    
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.8rem', borderRadius: '8px', fontSize: '0.85rem', borderLeft: '3px solid var(--accent-primary)', color: 'var(--text-secondary)', marginBottom: '1.2rem' }}>
                      <strong>Rationale:</strong> {analysisResult.rationale}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      {/* Strong Matches */}
                      {analysisResult.strong_matches && analysisResult.strong_matches.length > 0 && (
                        <div>
                          <h4 style={{ fontSize: '0.85rem', color: 'var(--accent-success)', marginBottom: '0.3rem', fontWeight: 700 }}>✓ Strong Matches</h4>
                          <ul style={{ paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                            {analysisResult.strong_matches.map((match: string) => (
                              <li key={match}>
                                <strong>{match}</strong>
                                {analysisResult.evidence_map?.[match] && (
                                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.05rem', fontStyle: 'italic' }}>
                                    ↳ {analysisResult.evidence_map[match]}
                                  </div>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Transferable Matches */}
                      {analysisResult.transferable_matches && analysisResult.transferable_matches.length > 0 && (
                        <div>
                          <h4 style={{ fontSize: '0.85rem', color: 'var(--accent-secondary)', marginBottom: '0.3rem', fontWeight: 700 }}>⇄ Transferable Matches</h4>
                          <ul style={{ paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                            {analysisResult.transferable_matches.map((item: any, idx: number) => (
                              <li key={idx}>
                                <strong>{item.required}</strong> (transferable from <em>{item.candidate_has}</em>)
                                {analysisResult.evidence_map?.[item.required] && (
                                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.05rem', fontStyle: 'italic' }}>
                                    ↳ {analysisResult.evidence_map[item.required]}
                                  </div>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Partial Matches */}
                      {analysisResult.partial_matches && analysisResult.partial_matches.length > 0 && (
                        <div>
                          <h4 style={{ fontSize: '0.85rem', color: 'var(--accent-warning)', marginBottom: '0.3rem', fontWeight: 700 }}>⚠ Partial Matches</h4>
                          <ul style={{ paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                            {analysisResult.partial_matches.map((match: string) => (
                              <li key={match}>
                                <strong>{match}</strong>
                                {analysisResult.evidence_map?.[match] && (
                                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.05rem', fontStyle: 'italic' }}>
                                    ↳ {analysisResult.evidence_map[match]}
                                  </div>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Missing Requirements */}
                      {analysisResult.missing_requirements && analysisResult.missing_requirements.length > 0 && (
                        <div>
                          <h4 style={{ fontSize: '0.85rem', color: 'var(--accent-error)', marginBottom: '0.3rem', fontWeight: 700 }}>✗ Missing Requirements</h4>
                          <ul style={{ paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                            {analysisResult.missing_requirements.map((missing: string) => (
                              <li key={missing} style={{ color: 'rgba(255,255,255,0.7)' }}>{missing}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* SIDEBAR FOR JOBS INTAKE & PARSING */}
            {activeTab === 'jobs' && (
              <div className="card" style={{ borderLeft: '4px solid var(--accent-primary)' }}>
                <h2 className="section-title">Job Analysis Workspace</h2>
                
                {selectedJob ? (
                  <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                    
                    {/* Header Summary */}
                    <div>
                      <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff' }}>{selectedJob.title}</h3>
                      <p style={{ fontSize: '0.9rem', color: 'var(--accent-secondary)', fontWeight: 500 }}>{selectedJob.company}</p>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>📍 {selectedJob.location || 'Location Not Specified'}</p>
                      {selectedJob.job_url && (
                        <a href={selectedJob.job_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', color: 'var(--accent-secondary)', textDecoration: 'none', display: 'block', marginTop: '0.4rem' }}>
                          🔗 View Job Posting Link
                        </a>
                      )}
                    </div>

                    {selectedJob.extracted_requirements ? (
                      <>
                        {/* Seniority & Experience */}
                        <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap' }}>
                          <span className="badge badge-applied" style={{ textTransform: 'none' }}>
                            👔 Seniority: {selectedJob.extracted_requirements.seniority || 'Not specified'}
                          </span>
                          <span className="badge badge-applied" style={{ textTransform: 'none' }}>
                            📅 Experience: {selectedJob.extracted_requirements.years_experience !== null ? `${selectedJob.extracted_requirements.years_experience}+ Years` : 'Not specified'}
                          </span>
                          <span className="badge badge-applied" style={{ textTransform: 'none' }}>
                            💼 Type: {selectedJob.extracted_requirements.employment_type || 'Full-time'}
                          </span>
                        </div>

                        {/* Run Fit Analysis Trigger */}
                        <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                          <button 
                            className="btn btn-primary" 
                            style={{ width: '100%', justifyContent: 'center' }} 
                            onClick={() => handleAnalyzeJobFit(selectedJob.id)}
                            disabled={actionLoading}
                          >
                            {actionLoading ? 'Analyzing...' : '⚡ Run Fit Analysis'}
                          </button>
                        </div>

                        {jobFitAnalysis && (
                          <div style={{ 
                            marginTop: '1rem', 
                            background: 'rgba(138, 43, 226, 0.05)', 
                            border: '1px solid var(--border-hover)', 
                            borderRadius: '12px', 
                            padding: '1rem', 
                            display: 'flex', 
                            flexDirection: 'column', 
                            gap: '1rem' 
                          }}>
                            {/* Match Score Indicator */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                              <div style={{ 
                                width: '56px', 
                                height: '56px', 
                                borderRadius: '50%', 
                                background: jobFitAnalysis.match_score >= 80 ? 'rgba(16, 185, 129, 0.15)' : jobFitAnalysis.match_score >= 50 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)', 
                                border: `2px solid ${jobFitAnalysis.match_score >= 80 ? 'var(--accent-success)' : jobFitAnalysis.match_score >= 50 ? 'var(--accent-warning)' : 'var(--accent-error)'}`, 
                                display: 'flex', 
                                alignItems: 'center', 
                                justifyContent: 'center', 
                                fontSize: '1.2rem', 
                                fontWeight: 'bold', 
                                color: jobFitAnalysis.match_score >= 80 ? 'var(--accent-success)' : jobFitAnalysis.match_score >= 50 ? 'var(--accent-warning)' : 'var(--accent-error)' 
                              }}>
                                {jobFitAnalysis.match_score}%
                              </div>
                              <div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Recommendation</div>
                                <span className={`badge badge-${jobFitAnalysis.recommendation === 'APPLY' ? 'offered' : jobFitAnalysis.recommendation === 'CONSIDER' ? 'interviewing' : 'rejected'}`}>
                                  {jobFitAnalysis.recommendation}
                                </span>
                              </div>
                            </div>
                            
                            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.6rem 0.8rem', borderRadius: '8px', fontSize: '0.8rem', borderLeft: '3px solid var(--accent-primary)', color: 'var(--text-secondary)' }}>
                              <strong>Rationale:</strong> {jobFitAnalysis.rationale}
                            </div>

                            {/* Strong Matches */}
                            {jobFitAnalysis.strong_matches && jobFitAnalysis.strong_matches.length > 0 && (
                              <div>
                                <h4 style={{ fontSize: '0.8rem', color: 'var(--accent-success)', marginBottom: '0.3rem', fontWeight: 700 }}>✓ Strong Matches</h4>
                                <ul style={{ paddingLeft: '1rem', fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                                  {jobFitAnalysis.strong_matches.map((match: string) => (
                                    <li key={match}>
                                      <strong>{match}</strong>
                                      {jobFitAnalysis.evidence_map?.[match] && (
                                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.05rem', fontStyle: 'italic' }}>
                                          ↳ {jobFitAnalysis.evidence_map[match]}
                                        </div>
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Transferable Matches */}
                            {jobFitAnalysis.transferable_matches && jobFitAnalysis.transferable_matches.length > 0 && (
                              <div>
                                <h4 style={{ fontSize: '0.8rem', color: 'var(--accent-secondary)', marginBottom: '0.3rem', fontWeight: 700 }}>⇄ Transferable Matches</h4>
                                <ul style={{ paddingLeft: '1rem', fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                                  {jobFitAnalysis.transferable_matches.map((item: any, idx: number) => (
                                    <li key={idx}>
                                      <strong>{item.required}</strong> (transferable from <em>{item.candidate_has}</em>)
                                      {jobFitAnalysis.evidence_map?.[item.required] && (
                                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.05rem', fontStyle: 'italic' }}>
                                          ↳ {jobFitAnalysis.evidence_map[item.required]}
                                        </div>
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Partial Matches */}
                            {jobFitAnalysis.partial_matches && jobFitAnalysis.partial_matches.length > 0 && (
                              <div>
                                <h4 style={{ fontSize: '0.8rem', color: 'var(--accent-warning)', marginBottom: '0.3rem', fontWeight: 700 }}>⚠ Partial Matches</h4>
                                <ul style={{ paddingLeft: '1rem', fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                                  {jobFitAnalysis.partial_matches.map((match: string) => (
                                    <li key={match}>
                                      <strong>{match}</strong>
                                      {jobFitAnalysis.evidence_map?.[match] && (
                                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.05rem', fontStyle: 'italic' }}>
                                          ↳ {jobFitAnalysis.evidence_map[match]}
                                        </div>
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Missing Requirements */}
                            {jobFitAnalysis.missing_requirements && jobFitAnalysis.missing_requirements.length > 0 && (
                              <div>
                                <h4 style={{ fontSize: '0.8rem', color: 'var(--accent-error)', marginBottom: '0.3rem', fontWeight: 700 }}>✗ Missing Requirements</h4>
                                <ul style={{ paddingLeft: '1rem', fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                                  {jobFitAnalysis.missing_requirements.map((missing: string) => (
                                    <li key={missing} style={{ color: 'rgba(255,255,255,0.7)' }}>{missing}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}

                        {jobFitAnalysis && (
                          <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <button 
                              className="btn btn-secondary" 
                              style={{ width: '100%', justifyContent: 'center', borderColor: 'goldenrod', color: 'goldenrod', background: 'rgba(218, 165, 32, 0.05)' }} 
                              onClick={() => handleGenerateSuggestions(selectedJob.id)}
                              disabled={actionLoading}
                            >
                              {actionLoading ? 'Generating...' : '✨ Generate Resume Suggestions'}
                            </button>
                          </div>
                        )}

                        {/* Skills lists */}
                        <div>
                          <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', fontWeight: 600 }}>Required Skills</h4>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginBottom: '0.8rem' }}>
                            {selectedJob.extracted_requirements.required_skills.length > 0 ? (
                              selectedJob.extracted_requirements.required_skills.map((skill: string) => (
                                <span key={skill} className="badge badge-applied" style={{ fontSize: '0.7rem' }}>{skill}</span>
                              ))
                            ) : (
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>None matched</span>
                            )}
                          </div>

                          <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', fontWeight: 600 }}>Preferred / Nice-to-Have</h4>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginBottom: '0.8rem' }}>
                            {selectedJob.extracted_requirements.preferred_skills.length > 0 ? (
                              selectedJob.extracted_requirements.preferred_skills.map((skill: string) => (
                                <span key={skill} className="badge badge-saved" style={{ fontSize: '0.7rem' }}>{skill}</span>
                              ))
                            ) : (
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>None matched</span>
                            )}
                          </div>

                          <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', fontWeight: 600 }}>Tools / Libraries</h4>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                            {selectedJob.extracted_requirements.tools.length > 0 ? (
                              selectedJob.extracted_requirements.tools.map((tool: string) => (
                                <span key={tool} className="badge badge-saved" style={{ fontSize: '0.7rem', borderColor: 'var(--accent-secondary)', color: 'var(--accent-secondary)' }}>{tool}</span>
                              ))
                            ) : (
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>None matched</span>
                            )}
                          </div>
                        </div>

                        {/* Soft Skills */}
                        {selectedJob.extracted_requirements.soft_skills.length > 0 && (
                          <div>
                            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', fontWeight: 600 }}>Soft Skills</h4>
                            <ul style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', paddingLeft: '1.2rem', lineHeight: '1.4' }}>
                              {selectedJob.extracted_requirements.soft_skills.map((s: string) => (
                                <li key={s}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Red Flags warning card */}
                        {selectedJob.extracted_requirements.red_flags.length > 0 && (
                          <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', padding: '0.8rem', borderRadius: '10px' }}>
                            <h4 style={{ fontSize: '0.85rem', color: 'var(--accent-error)', display: 'flex', alignItems: 'center', gap: '0.3rem', fontWeight: 700, marginBottom: '0.4rem' }}>
                              🚨 Detected Red Flags
                            </h4>
                            <ul style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', paddingLeft: '1.1rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                              {selectedJob.extracted_requirements.red_flags.map((rf: string, idx: number) => (
                                <li key={idx} style={{ color: 'rgba(255,255,255,0.85)' }}>{rf}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.8rem' }}>
                          Requirements have not been parsed for this job yet.
                        </p>
                        <button className="btn btn-primary" style={{ width: '100%', fontSize: '0.8rem', justifyContent: 'center' }} onClick={() => handleAnalyzeJob(selectedJob.id)}>
                          ⚙️ Extract Requirements
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '1.5rem', textAlign: 'center' }}>
                    Select an ingested job description from the list to review the parsed requirements.
                  </p>
                )}
              </div>
            )}

            {/* SIDEBAR FOR PROFILE CONFIRMATION & REVIEW */}
            {activeTab === 'profile' && (
              <div className="card">
                <h2 className="section-title">Manage Resumes</h2>
                <div style={{ marginTop: '1rem' }}>
                  <label className="btn btn-secondary" style={{ display: 'flex', justifyContent: 'center', cursor: 'pointer', borderStyle: 'dashed' }}>
                    {uploading ? '📤 Uploading...' : '📄 Upload Resume (.txt, .md, .pdf, .docx)'}
                    <input type="file" onChange={handleFileUpload} accept=".txt,.md,.pdf,.docx" style={{ display: 'none' }} disabled={uploading} />
                  </label>
                </div>
                {resumes.length > 0 ? (
                  <div style={{ marginTop: '1.5rem' }}>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                      Select Uploaded Resume:
                    </label>
                    <select className="input" value={selectedResumeId} onChange={(e) => setSelectedResumeId(e.target.value)}>
                      {resumes.map(r => (
                        <option key={r.id} value={r.id}>{r.file_name}</option>
                      ))}
                    </select>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.8rem' }}>
                      <button className="btn btn-primary" style={{ flex: 1, padding: '0.5rem', fontSize: '0.85rem', justifyContent: 'center' }} onClick={() => handleParseResume(selectedResumeId)} disabled={actionLoading}>
                        ⚙️ Parse to Profile
                      </button>
                    </div>
                  </div>
                ) : (
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '1rem', textAlign: 'center' }}>No resumes uploaded yet.</p>
                )}
              </div>
            )}

            {activeTab === 'versions' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                
                {/* Compose Control Panel */}
                <div className="card">
                  <h2 className="section-title">Compose Tailored Resume</h2>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.4rem', marginBottom: '1.2rem' }}>
                    Select an analyzed job posting to compile approved suggestions.
                  </p>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                    <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Select Job Posting:</label>
                    <select 
                      className="input" 
                      value={versionsJobId} 
                      onChange={(e) => setVersionsJobId(e.target.value)}
                    >
                      <option value="">-- Select Job Posting --</option>
                      {jobs.map(j => (
                        <option key={j.id} value={j.id}>{j.title} at {j.company}</option>
                      ))}
                    </select>

                    <button 
                      className="btn btn-primary"
                      style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem' }}
                      onClick={async () => {
                        if (!versionsJobId) {
                          showToast('Please select a job posting first.', 'error');
                          return;
                        }
                        try {
                          setActionLoading(true);
                          const res = await authFetch(`${API_URL}/resume-versions`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ job_id: versionsJobId })
                          });
                          if (!res.ok) {
                            const data = await res.json();
                            throw new Error(data.detail || 'Failed to compose resume version');
                          }
                          const data = await res.json();
                          showToast('Resume version composed successfully!', 'success');
                          setResumeVersions(prev => [data, ...prev]);
                          setSelectedVersionId(data.id);
                          // Re-fetch versions & apps
                          const verRes = await authFetch(`${API_URL}/resume-versions`);
                          if (verRes.ok) setResumeVersions(await verRes.json());
                          const appsRes = await authFetch(`${API_URL}/applications`);
                          if (appsRes.ok) setApplications(await appsRes.json());
                        } catch (err: any) {
                          showToast(err.message, 'error');
                        } finally {
                          setActionLoading(false);
                        }
                      }}
                      disabled={actionLoading}
                    >
                      ⚙️ Compose Tailored Resume
                    </button>
                  </div>
                </div>

                {/* Resume Version History List */}
                <div className="card">
                  <h2 className="section-title">Version History</h2>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.4rem', marginBottom: '1.2rem' }}>
                    Select a versioned resume draft below to view the bullet-level diff workspace.
                  </p>

                  {resumeVersions.length === 0 ? (
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1rem 0' }}>
                      No versions generated yet.
                    </p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                      {resumeVersions.map(v => {
                        const job = jobs.find(j => j.id === v.job_id);
                        const isSelected = v.id === selectedVersionId;
                        const traceability = v.content_json._traceability || {};
                        const count = Object.keys(traceability).length;

                        return (
                          <div 
                            key={v.id}
                            onClick={() => setSelectedVersionId(v.id)}
                            style={{
                              padding: '0.8rem 1rem',
                              background: isSelected ? 'rgba(255, 255, 255, 0.04)' : 'rgba(255, 255, 255, 0.01)',
                              border: isSelected ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                              borderRadius: '8px',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '0.3rem'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span className={`badge badge-${
                                v.status === 'ACTIVE' ? 'offered' : 
                                v.status === 'INACTIVE' ? 'rejected' : 
                                'saved'
                              }`} style={{ fontSize: '0.65rem' }}>
                                {v.status}
                              </span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {new Date(v.created_at).toLocaleDateString()}
                              </span>
                            </div>

                            <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: isSelected ? 'var(--accent-primary)' : '#fff', margin: 0 }}>
                              {job ? job.title : 'Target Position'}
                            </h4>
                            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0 }}>
                              🏢 {job ? job.company : 'Company'}
                            </p>
                            
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.4rem', borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '0.4rem' }}>
                              <span style={{ fontSize: '0.72rem', color: 'var(--accent-secondary)' }}>
                                💡 Applied Suggestions: {count}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

              </div>
            )}

            {/* Feedback Collection Widget */}
            <div className="card" style={{ borderTop: '4px solid var(--accent-secondary)', marginTop: '2rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.4rem', color: '#fff' }}>
                💬 Private Beta Feedback
              </h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Help us improve! Rate your experience and share your thoughts.
              </p>
              
              <form onSubmit={handleFeedbackSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Rating:</span>
                  {[1, 2, 3, 4, 5].map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setFeedbackRating(num)}
                      style={{
                        background: 'none',
                        border: 'none',
                        fontSize: '1.25rem',
                        cursor: 'pointer',
                        color: num <= feedbackRating ? '#fbbf24' : '#4b5563',
                        transition: 'transform 0.15s ease',
                        padding: '0.1rem'
                      }}
                    >
                      ★
                    </button>
                  ))}
                </div>

                <textarea
                  placeholder="Share suggestions, report bugs, or request features..."
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  className="input"
                  style={{ fontSize: '0.8rem', minHeight: '60px', resize: 'vertical' }}
                  required
                  disabled={submittingFeedback}
                />

                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '0.45rem', fontSize: '0.85rem', justifyContent: 'center' }}
                  disabled={submittingFeedback}
                >
                  {submittingFeedback ? 'Sending...' : '📤 Send Feedback'}
                </button>
              </form>
            </div>
            
          </div>
        </div>
      </>
    )}

      {/* Toast Notifications */}
      <div style={{ position: 'fixed', top: '24px', right: '24px', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '380px', width: '100%' }}>
        {notifications.map(n => (
          <div key={n.id} style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1rem 1.2rem',
            background: '#161622',
            border: '1px solid rgba(255,255,255,0.08)',
            borderLeft: `4px solid ${
              n.type === 'success' ? 'var(--accent-success)' :
              n.type === 'error' ? 'var(--accent-error)' :
              n.type === 'warning' ? 'var(--accent-warning)' :
              'var(--accent-primary)'
            }`,
            borderRadius: '8px',
            boxShadow: '0 8px 30px rgba(0,0,0,0.3)'
          }}>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginRight: '1rem', whiteSpace: 'pre-line' }}>
              {n.message}
            </div>
            <button 
              onClick={() => removeToast(n.id)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '1.1rem',
                padding: '0.2rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Close"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Custom Confirmation Modal */}
      {confirmModal.isOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9998
        }}>
          <div className="card" style={{
            width: '400px',
            padding: '1.8rem',
            borderRadius: '12px',
            background: '#161622',
            border: '1px solid rgba(255,255,255,0.08)',
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
          }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.8rem' }}>Confirm Action</h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '1.8rem' }}>
              {confirmModal.message}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.8rem' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
                style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
              >
                Cancel
              </button>
              <button 
                className="btn" 
                onClick={confirmModal.onConfirm}
                style={{ 
                  padding: '0.5rem 1rem', 
                  fontSize: '0.85rem',
                  background: confirmModal.message.toLowerCase().includes('delete') ? 'var(--accent-error)' : 'var(--accent-primary)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
