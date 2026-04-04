import { useState, useEffect } from 'react'
import { mealAPI, menuAPI } from '../services/api'
import toast from 'react-hot-toast'
import { FiCalendar, FiDollarSign, FiZap, FiRefreshCw, FiCamera, FiChevronDown } from 'react-icons/fi'

export default function MealPlan() {
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [duration, setDuration] = useState('7')
  const [menuHistory, setMenuHistory] = useState([])
  const [selectedMenuId, setSelectedMenuId] = useState('')

  // Fetch menu history on load
  useEffect(() => {
    const fetchMenus = async () => {
      try {
        const response = await menuAPI.getHistory()
        const menus = response.data.menus || []
        setMenuHistory(menus)
        if (menus.length > 0) {
          setSelectedMenuId(menus[0].id) // Select most recent by default
        }
      } catch (error) {
        console.error('Failed to load menu history')
      }
    }
    fetchMenus()
  }, [])

  const generatePlan = async () => {
    if (!selectedMenuId) {
      toast.error('Please select a menu first')
      return
    }

    setLoading(true)
    try {
      const response = await mealAPI.generateFromScanned(parseInt(duration), selectedMenuId)
      setPlan(response.data)
      toast.success(`Generated ${duration}-day plan!`)
    } catch (error) {
      const detail = error.response?.data?.detail || 'Failed to generate plan'
      const hint = error.response?.data?.hint
      if (hint) {
        toast.error(`${detail}\n${hint}`)
      } else {
        toast.error(detail)
      }
    }
    setLoading(false)
  }

  const getMealIcon = (slot) => {
    switch (slot) {
      case 'breakfast': return '🌅'
      case 'morning_snack': return '🍎'
      case 'lunch': return '🍱'
      case 'evening_snack': return '☕'
      case 'dinner': return '🌙'
      default: return '🍽️'
    }
  }

  const selectedMenu = menuHistory.find(m => m.id === selectedMenuId)

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Meal Planner</h1>
          <p className="text-gray-500 mt-1">AI-optimized meals from your scanned menus</p>
        </div>

        <div className="flex flex-col md:flex-row items-start md:items-center space-y-2 md:space-y-0 md:space-x-4 mt-4 md:mt-0">
          {/* Menu Selector */}
          <div className="relative">
            <select
              value={selectedMenuId}
              onChange={(e) => setSelectedMenuId(e.target.value)}
              className="input-field w-48 pr-8 appearance-none"
            >
              <option value="">Select a menu...</option>
              {menuHistory.map(menu => (
                <option key={menu.id} value={menu.id}>
                  {menu.name} ({menu.total_items} items)
                </option>
              ))}
            </select>
            <FiChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>

          <select
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            className="input-field w-auto"
          >
            <option value="1">1 Day</option>
            <option value="3">3 Days</option>
            <option value="7">7 Days</option>
          </select>
          <button
            onClick={generatePlan}
            disabled={loading || !selectedMenuId}
            className="btn-primary flex items-center space-x-2"
          >
            {loading ? (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            ) : (
              <>
                <FiRefreshCw />
                <span>Generate Plan</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Selected Menu Info */}
      {selectedMenu && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center space-x-2 text-blue-800">
            <FiCamera className="w-5 h-5" />
            <span className="font-medium">Using: {selectedMenu.name}</span>
          </div>
          <div className="mt-2 text-sm text-blue-700">
            {selectedMenu.total_items} items • {selectedMenu.veg_items} veg • {selectedMenu.non_veg_items} non-veg
          </div>
        </div>
      )}

      {menuHistory.length === 0 && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-yellow-800 font-medium">No saved menus found</div>
          <div className="mt-1 text-sm text-yellow-700">
            Go to <a href="/menu-upload" className="underline font-medium">Menu Scanner</a> to scan and save a menu first.
          </div>
        </div>
      )}

      {/* Plan Summary */}
      {plan && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="card bg-primary-50 border border-primary-200">
            <div className="flex items-center space-x-3">
              <FiCalendar className="w-8 h-8 text-primary-600" />
              <div>
                <p className="text-sm text-primary-600">Duration</p>
                <p className="text-xl font-bold text-primary-800">{plan.summary.total_days} Days</p>
              </div>
            </div>
          </div>
          <div className="card bg-green-50 border border-green-200">
            <div className="flex items-center space-x-3">
              <FiDollarSign className="w-8 h-8 text-green-600" />
              <div>
                <p className="text-sm text-green-600">Total Cost</p>
                <p className="text-xl font-bold text-green-800">₹{plan.summary.total_cost}</p>
              </div>
            </div>
          </div>
          <div className="card bg-orange-50 border border-orange-200">
            <div className="flex items-center space-x-3">
              <FiZap className="w-8 h-8 text-orange-600" />
              <div>
                <p className="text-sm text-orange-600">Avg. Calories</p>
                <p className="text-xl font-bold text-orange-800">{plan.summary.average_daily_calories} kcal</p>
              </div>
            </div>
          </div>
          <div className="card bg-blue-50 border border-blue-200">
            <div className="flex items-center space-x-3">
              <FiDollarSign className="w-8 h-8 text-blue-600" />
              <div>
                <p className="text-sm text-blue-600">Budget Used</p>
                <p className="text-xl font-bold text-blue-800">{plan.summary.budget_used_pct}%</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Daily Plans */}
      {plan && (
        <div className="space-y-6">
          {(plan.days || plan.plan || []).map((day) => {
            // Handle both formats: days (from scanned) has meals as object, plan (from db) has meals as array
            const mealsData = day.meals
            const mealsArray = Array.isArray(mealsData) 
              ? mealsData 
              : Object.entries(mealsData || {}).map(([slot, items]) => ({
                  slot,
                  items: items || [],
                  total_calories: items?.reduce((sum, i) => sum + (i.calories || 0), 0) || 0,
                  total_cost: items?.reduce((sum, i) => sum + (i.price || 0), 0) || 0
                }))
            
            // Get daily totals
            const dailyCalories = day.daily_calories || day.totals?.calories || 
              mealsArray.reduce((sum, m) => sum + (m.total_calories || 0), 0)
            const dailyCost = day.daily_cost || day.totals?.cost ||
              mealsArray.reduce((sum, m) => sum + (m.total_cost || 0), 0)
            
            return (
              <div key={day.day} className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Day {day.day}</h3>
                  <div className="flex items-center space-x-4 text-sm">
                    <span className="text-gray-500">
                      <span className="font-medium">{dailyCalories.toFixed(0)}</span> kcal
                    </span>
                    <span className="text-green-600 font-medium">
                      ₹{dailyCost.toFixed(0)}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {mealsArray.map((meal) => (
                    <div 
                      key={meal.slot} 
                      className="bg-gray-50 rounded-lg p-4"
                    >
                      <div className="flex items-center space-x-2 mb-3">
                        <span className="text-xl">{getMealIcon(meal.slot)}</span>
                        <span className="font-medium capitalize">{meal.slot.replace('_', ' ')}</span>
                      </div>

                      {meal.items && meal.items.length > 0 ? (
                        <div className="space-y-2">
                          {meal.items.map((item, idx) => (
                            <div key={idx} className="flex justify-between text-sm">
                              <span className="text-gray-700">
                                {item.is_veg && '🟢 '}{item.name}
                              </span>
                              <span className="text-gray-500">₹{(item.price || 0).toFixed(0)}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-400 text-sm">No items</p>
                      )}

                      <div className="mt-3 pt-2 border-t border-gray-200 flex justify-between text-xs text-gray-500">
                        <span>{(meal.total_calories || meal.items?.reduce((s, i) => s + (i.calories || 0), 0) || 0).toFixed(0)} kcal</span>
                        <span>₹{(meal.total_cost || meal.items?.reduce((s, i) => s + (i.price || 0), 0) || 0).toFixed(0)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Empty State */}
      {!plan && !loading && (
        <div className="card text-center py-16">
          <div className="text-6xl mb-4">🍽️</div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">
            No Meal Plan Yet
          </h3>
          <p className="text-gray-500 mb-6">
            {menuHistory.length > 0 
              ? 'Select a menu and generate a personalized meal plan.'
              : 'Scan a canteen menu first, then generate your meal plan.'}
          </p>
          {menuHistory.length > 0 ? (
            <button
              onClick={generatePlan}
              disabled={!selectedMenuId}
              className="btn-primary inline-flex items-center space-x-2"
            >
              <FiCalendar />
              <span>Generate Your First Plan</span>
            </button>
          ) : (
            <a href="/menu-upload" className="btn-primary inline-flex items-center space-x-2">
              <FiCamera />
              <span>Scan a Menu</span>
            </a>
          )}
        </div>
      )}
    </div>
  )
}
