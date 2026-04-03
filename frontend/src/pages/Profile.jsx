import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { userAPI } from '../services/api'
import toast from 'react-hot-toast'
import { FiSave, FiUser, FiHeart, FiDollarSign, FiClock } from 'react-icons/fi'

export default function Profile() {
  const { user, fetchUser } = useAuth()
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')

  const [profile, setProfile] = useState({
    age: '',
    gender: '',
    height: '',
    weight: '',
    activity_level: 'moderate',
    goal: 'maintenance'
  })

  const [dietary, setDietary] = useState({
    diet_type: 'veg',
    allergies: [],
    disliked_foods: [],
    preferred_cuisines: []
  })

  const [budget, setBudget] = useState({
    daily_budget: 150,
    strict_mode: false
  })

  const [mealConfig, setMealConfig] = useState({
    enabled_meals: ['breakfast', 'lunch', 'dinner']
  })

  useEffect(() => {
    if (user) {
      setProfile({
        age: user.profile?.age || '',
        gender: user.profile?.gender || '',
        height: user.profile?.height || '',
        weight: user.profile?.weight || '',
        activity_level: user.profile?.activity_level || 'moderate',
        goal: user.profile?.goal || 'maintenance'
      })
      setDietary({
        diet_type: user.dietary_preferences?.diet_type || 'veg',
        allergies: user.dietary_preferences?.allergies || [],
        disliked_foods: user.dietary_preferences?.disliked_foods || [],
        preferred_cuisines: user.dietary_preferences?.preferred_cuisines || []
      })
      setBudget({
        daily_budget: user.budget_settings?.daily_budget || 150,
        strict_mode: user.budget_settings?.strict_mode || false
      })
    }
  }, [user])

  const handleProfileSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await userAPI.updateProfile(profile)
      await fetchUser()
      toast.success('Profile updated successfully!')
    } catch (error) {
      toast.error('Failed to update profile')
    }
    setLoading(false)
  }

  const handleDietarySubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await userAPI.updateDietaryPreferences(dietary)
      await fetchUser()
      toast.success('Dietary preferences updated!')
    } catch (error) {
      toast.error('Failed to update dietary preferences')
    }
    setLoading(false)
  }

  const handleBudgetSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await userAPI.updateBudget(budget)
      await fetchUser()
      toast.success('Budget settings updated!')
    } catch (error) {
      toast.error('Failed to update budget')
    }
    setLoading(false)
  }

  const handleMealConfigSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await userAPI.updateMealConfig(mealConfig)
      await fetchUser()
      toast.success('Meal configuration updated!')
    } catch (error) {
      toast.error('Failed to update meal configuration')
    }
    setLoading(false)
  }

  const toggleAllergy = (allergy) => {
    setDietary(prev => ({
      ...prev,
      allergies: prev.allergies.includes(allergy)
        ? prev.allergies.filter(a => a !== allergy)
        : [...prev.allergies, allergy]
    }))
  }

  const toggleMeal = (meal) => {
    setMealConfig(prev => ({
      ...prev,
      enabled_meals: prev.enabled_meals.includes(meal)
        ? prev.enabled_meals.filter(m => m !== meal)
        : [...prev.enabled_meals, meal]
    }))
  }

  const commonAllergies = ['nuts', 'dairy', 'gluten', 'eggs', 'soy', 'fish', 'shellfish']
  const cuisines = ['South Indian', 'North Indian', 'Chinese', 'Western', 'Hyderabadi', 'Mumbai']
  const mealSlots = [
    { id: 'breakfast', label: 'Breakfast' },
    { id: 'morning_snack', label: 'Morning Snack' },
    { id: 'lunch', label: 'Lunch' },
    { id: 'evening_snack', label: 'Evening Snack' },
    { id: 'dinner', label: 'Dinner' }
  ]

  const tabs = [
    { id: 'profile', label: 'Health Profile', icon: FiUser },
    { id: 'dietary', label: 'Dietary Preferences', icon: FiHeart },
    { id: 'budget', label: 'Budget', icon: FiDollarSign },
    { id: 'meals', label: 'Meal Settings', icon: FiClock }
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Profile Settings</h1>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === id
                ? 'bg-primary-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Icon className="w-4 h-4" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Health Profile */}
      {activeTab === 'profile' && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Health Profile</h2>
          <form onSubmit={handleProfileSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Age</label>
                <input
                  type="number"
                  value={profile.age}
                  onChange={(e) => setProfile({ ...profile, age: parseInt(e.target.value) || '' })}
                  className="input-field"
                  placeholder="25"
                  min="10"
                  max="100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                <select
                  value={profile.gender}
                  onChange={(e) => setProfile({ ...profile, gender: e.target.value })}
                  className="input-field"
                >
                  <option value="">Select gender</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Height (cm)</label>
                <input
                  type="number"
                  value={profile.height}
                  onChange={(e) => setProfile({ ...profile, height: parseFloat(e.target.value) || '' })}
                  className="input-field"
                  placeholder="170"
                  min="100"
                  max="250"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Weight (kg)</label>
                <input
                  type="number"
                  value={profile.weight}
                  onChange={(e) => setProfile({ ...profile, weight: parseFloat(e.target.value) || '' })}
                  className="input-field"
                  placeholder="70"
                  min="30"
                  max="300"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Activity Level</label>
                <select
                  value={profile.activity_level}
                  onChange={(e) => setProfile({ ...profile, activity_level: e.target.value })}
                  className="input-field"
                >
                  <option value="sedentary">Sedentary (little or no exercise)</option>
                  <option value="light">Light (exercise 1-3 days/week)</option>
                  <option value="moderate">Moderate (exercise 3-5 days/week)</option>
                  <option value="active">Active (exercise 6-7 days/week)</option>
                  <option value="very_active">Very Active (hard exercise daily)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Goal</label>
                <select
                  value={profile.goal}
                  onChange={(e) => setProfile({ ...profile, goal: e.target.value })}
                  className="input-field"
                >
                  <option value="weight_loss">Weight Loss</option>
                  <option value="maintenance">Maintenance</option>
                  <option value="weight_gain">Weight Gain</option>
                </select>
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-primary flex items-center space-x-2">
              <FiSave />
              <span>{loading ? 'Saving...' : 'Save Profile'}</span>
            </button>
          </form>
        </div>
      )}

      {/* Dietary Preferences */}
      {activeTab === 'dietary' && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Dietary Preferences</h2>
          <form onSubmit={handleDietarySubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Diet Type</label>
              <div className="flex flex-wrap gap-3">
                {['veg', 'non_veg', 'vegan', 'eggetarian'].map(type => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setDietary({ ...dietary, diet_type: type })}
                    className={`px-4 py-2 rounded-lg font-medium capitalize ${
                      dietary.diet_type === type
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {type.replace('_', '-')}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Allergies</label>
              <div className="flex flex-wrap gap-2">
                {commonAllergies.map(allergy => (
                  <button
                    key={allergy}
                    type="button"
                    onClick={() => toggleAllergy(allergy)}
                    className={`px-3 py-1 rounded-full text-sm capitalize ${
                      dietary.allergies.includes(allergy)
                        ? 'bg-red-100 text-red-700 border border-red-300'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {allergy}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Preferred Cuisines</label>
              <div className="flex flex-wrap gap-2">
                {cuisines.map(cuisine => (
                  <button
                    key={cuisine}
                    type="button"
                    onClick={() => setDietary(prev => ({
                      ...prev,
                      preferred_cuisines: prev.preferred_cuisines.includes(cuisine)
                        ? prev.preferred_cuisines.filter(c => c !== cuisine)
                        : [...prev.preferred_cuisines, cuisine]
                    }))}
                    className={`px-3 py-1 rounded-full text-sm ${
                      dietary.preferred_cuisines.includes(cuisine)
                        ? 'bg-primary-100 text-primary-700 border border-primary-300'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {cuisine}
                  </button>
                ))}
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary flex items-center space-x-2">
              <FiSave />
              <span>{loading ? 'Saving...' : 'Save Preferences'}</span>
            </button>
          </form>
        </div>
      )}

      {/* Budget Settings */}
      {activeTab === 'budget' && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Budget Settings</h2>
          <form onSubmit={handleBudgetSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Daily Budget (₹)
              </label>
              <input
                type="number"
                value={budget.daily_budget}
                onChange={(e) => setBudget({ ...budget, daily_budget: parseFloat(e.target.value) || 0 })}
                className="input-field"
                min="50"
                max="1000"
              />
              <p className="text-sm text-gray-500 mt-1">
                Recommended: ₹100-200 for balanced nutrition
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="strict_mode"
                checked={budget.strict_mode}
                onChange={(e) => setBudget({ ...budget, strict_mode: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <label htmlFor="strict_mode" className="text-sm text-gray-700">
                Strict Mode (never exceed daily budget)
              </label>
            </div>

            <button type="submit" disabled={loading} className="btn-primary flex items-center space-x-2">
              <FiSave />
              <span>{loading ? 'Saving...' : 'Save Budget'}</span>
            </button>
          </form>
        </div>
      )}

      {/* Meal Configuration */}
      {activeTab === 'meals' && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Meal Configuration</h2>
          <form onSubmit={handleMealConfigSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Enable Meals
              </label>
              <div className="space-y-2">
                {mealSlots.map(slot => (
                  <label key={slot.id} className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={mealConfig.enabled_meals.includes(slot.id)}
                      onChange={() => toggleMeal(slot.id)}
                      className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-gray-700">{slot.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary flex items-center space-x-2">
              <FiSave />
              <span>{loading ? 'Saving...' : 'Save Configuration'}</span>
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
