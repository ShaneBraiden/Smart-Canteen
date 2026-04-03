import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { userAPI, recommendationAPI } from '../services/api'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js'
import { Doughnut, Bar } from 'react-chartjs-2'
import { FiActivity, FiTarget, FiDollarSign, FiTrendingUp } from 'react-icons/fi'
import toast from 'react-hot-toast'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

export default function Dashboard() {
  const { user } = useAuth()
  const [healthMetrics, setHealthMetrics] = useState(null)
  const [macroTargets, setMacroTargets] = useState(null)
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [metricsRes, macrosRes, insightsRes] = await Promise.all([
        userAPI.getHealthMetrics(),
        userAPI.getMacroTargets().catch(() => null),
        recommendationAPI.getInsights()
      ])
      
      setHealthMetrics(metricsRes.data)
      if (macrosRes) setMacroTargets(macrosRes.data)
      setInsights(insightsRes.data)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getBMIColor = (category) => {
    switch (category?.toLowerCase()) {
      case 'underweight': return 'text-blue-500'
      case 'normal': return 'text-green-500'
      case 'overweight': return 'text-yellow-500'
      case 'obese': return 'text-red-500'
      default: return 'text-gray-500'
    }
  }

  const macroChartData = macroTargets ? {
    labels: ['Protein', 'Carbs', 'Fats'],
    datasets: [{
      data: [macroTargets.protein_pct, macroTargets.carbs_pct, macroTargets.fats_pct],
      backgroundColor: ['#22c55e', '#3b82f6', '#f97316'],
      borderWidth: 0
    }]
  } : null

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const profileComplete = user?.profile?.age && user?.profile?.height && user?.profile?.weight

  return (
    <div className="max-w-6xl mx-auto">
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">
          Welcome, {user?.username || 'User'}! 👋
        </h1>
        <p className="text-gray-500 mt-1">Here's your nutrition dashboard</p>
      </div>

      {!profileComplete && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-yellow-800">
            ⚠️ Complete your profile to get personalized meal plans and health insights.
            <a href="/profile" className="ml-2 text-yellow-600 underline font-medium">
              Complete Profile →
            </a>
          </p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* BMI Card */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">BMI</p>
              <p className="text-2xl font-bold">{healthMetrics?.bmi?.toFixed(1) || '-'}</p>
              <p className={`text-sm font-medium ${getBMIColor(healthMetrics?.bmi_category)}`}>
                {healthMetrics?.bmi_category || 'Complete profile'}
              </p>
            </div>
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
              <FiActivity className="w-6 h-6 text-primary-600" />
            </div>
          </div>
        </div>

        {/* Daily Calories */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Daily Target</p>
              <p className="text-2xl font-bold">{healthMetrics?.target_calories?.toFixed(0) || '-'}</p>
              <p className="text-sm text-gray-500">kcal/day</p>
            </div>
            <div className="w-12 h-12 bg-accent-100 rounded-full flex items-center justify-center">
              <FiTarget className="w-6 h-6 text-accent-600" />
            </div>
          </div>
        </div>

        {/* Daily Budget */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Daily Budget</p>
              <p className="text-2xl font-bold">₹{user?.budget_settings?.daily_budget || '-'}</p>
              <p className="text-sm text-gray-500">per day</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <FiDollarSign className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        {/* Goal */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Goal</p>
              <p className="text-2xl font-bold capitalize">
                {user?.profile?.goal?.replace('_', ' ') || '-'}
              </p>
              <p className="text-sm text-gray-500">current focus</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <FiTrendingUp className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Macro Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Macro Distribution</h3>
          {macroChartData ? (
            <div className="flex items-center justify-center">
              <div className="w-64 h-64">
                <Doughnut 
                  data={macroChartData} 
                  options={{ 
                    plugins: { 
                      legend: { position: 'bottom' } 
                    },
                    cutout: '60%'
                  }} 
                />
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">Complete profile to see macro targets</p>
          )}
          {macroTargets && (
            <div className="grid grid-cols-3 gap-4 mt-4 text-center">
              <div>
                <p className="text-lg font-bold text-green-600">{macroTargets.protein_g}g</p>
                <p className="text-sm text-gray-500">Protein</p>
              </div>
              <div>
                <p className="text-lg font-bold text-blue-600">{macroTargets.carbs_g}g</p>
                <p className="text-sm text-gray-500">Carbs</p>
              </div>
              <div>
                <p className="text-lg font-bold text-orange-600">{macroTargets.fats_g}g</p>
                <p className="text-sm text-gray-500">Fats</p>
              </div>
            </div>
          )}
        </div>

        {/* Insights */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Personalized Insights</h3>
          {insights?.insights?.length > 0 ? (
            <div className="space-y-4">
              {insights.insights.map((insight, index) => (
                <div 
                  key={index}
                  className={`p-4 rounded-lg ${
                    insight.type === 'tip' ? 'bg-green-50' :
                    insight.type === 'budget' ? 'bg-yellow-50' : 'bg-blue-50'
                  }`}
                >
                  <h4 className="font-medium text-gray-800">{insight.title}</h4>
                  <p className="text-sm text-gray-600 mt-1">{insight.message}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">Complete profile for insights</p>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a 
            href="/meal-plan" 
            className="p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors"
          >
            <h4 className="font-medium text-gray-800">Generate Meal Plan</h4>
            <p className="text-sm text-gray-500 mt-1">Get AI-optimized meals for your budget</p>
          </a>
          <a 
            href="/menu-upload" 
            className="p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors"
          >
            <h4 className="font-medium text-gray-800">Scan Menu</h4>
            <p className="text-sm text-gray-500 mt-1">Upload a menu image to analyze</p>
          </a>
          <a 
            href="/profile" 
            className="p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors"
          >
            <h4 className="font-medium text-gray-800">Update Profile</h4>
            <p className="text-sm text-gray-500 mt-1">Adjust your preferences and goals</p>
          </a>
        </div>
      </div>
    </div>
  )
}
