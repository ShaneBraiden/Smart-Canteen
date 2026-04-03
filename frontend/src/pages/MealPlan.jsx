import { useState } from 'react'
import { mealAPI } from '../services/api'
import toast from 'react-hot-toast'
import { FiCalendar, FiDollarSign, FiZap, FiRefreshCw } from 'react-icons/fi'

export default function MealPlan() {
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [duration, setDuration] = useState('7')

  const generatePlan = async () => {
    setLoading(true)
    try {
      const response = await mealAPI.generatePlan(duration)
      setPlan(response.data)
      toast.success(`Generated ${duration}-day meal plan!`)
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate plan')
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

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Meal Planner</h1>
          <p className="text-gray-500 mt-1">AI-optimized meals for your budget and goals</p>
        </div>

        <div className="flex items-center space-x-4 mt-4 md:mt-0">
          <select
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            className="input-field w-auto"
          >
            <option value="3">3 Days</option>
            <option value="7">7 Days</option>
            <option value="30">30 Days</option>
          </select>
          <button
            onClick={generatePlan}
            disabled={loading}
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
          {plan.plan.map((day) => (
            <div key={day.day} className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Day {day.day}</h3>
                <div className="flex items-center space-x-4 text-sm">
                  <span className="text-gray-500">
                    <span className="font-medium">{day.daily_calories.toFixed(0)}</span> kcal
                  </span>
                  <span className="text-green-600 font-medium">
                    ₹{day.daily_cost.toFixed(0)}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {day.meals.map((meal) => (
                  <div 
                    key={meal.slot} 
                    className="bg-gray-50 rounded-lg p-4"
                  >
                    <div className="flex items-center space-x-2 mb-3">
                      <span className="text-xl">{getMealIcon(meal.slot)}</span>
                      <span className="font-medium capitalize">{meal.slot.replace('_', ' ')}</span>
                    </div>

                    {meal.items.length > 0 ? (
                      <div className="space-y-2">
                        {meal.items.map((item, idx) => (
                          <div key={idx} className="flex justify-between text-sm">
                            <span className="text-gray-700">
                              {item.is_veg && '🟢 '}{item.name}
                            </span>
                            <span className="text-gray-500">₹{item.price}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-gray-400 text-sm">No items</p>
                    )}

                    <div className="mt-3 pt-2 border-t border-gray-200 flex justify-between text-xs text-gray-500">
                      <span>{meal.total_calories.toFixed(0)} kcal</span>
                      <span>₹{meal.total_cost.toFixed(0)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
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
            Generate a personalized meal plan optimized for your budget and nutrition goals.
          </p>
          <button
            onClick={generatePlan}
            className="btn-primary inline-flex items-center space-x-2"
          >
            <FiCalendar />
            <span>Generate Your First Plan</span>
          </button>
        </div>
      )}
    </div>
  )
}
