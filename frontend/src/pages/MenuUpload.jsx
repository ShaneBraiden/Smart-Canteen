import { useState, useEffect } from 'react'
import { menuAPI } from '../services/api'
import toast from 'react-hot-toast'
import { FiUpload, FiCamera, FiCheck, FiX, FiSearch, FiTrash2, FiRefreshCw, FiClock, FiEdit2, FiSave } from 'react-icons/fi'

export default function MenuUpload() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [menuName, setMenuName] = useState('')
  const [menuHistory, setMenuHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [editingMenuId, setEditingMenuId] = useState(null)
  const [editingName, setEditingName] = useState('')

  useEffect(() => {
    loadMenuHistory()
  }, [])

  const loadMenuHistory = async () => {
    try {
      const response = await menuAPI.getHistory()
      setMenuHistory(response.data.menus || [])
    } catch (error) {
      console.error('Failed to load menu history:', error)
    }
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setPreview(URL.createObjectURL(selectedFile))
      setResult(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      toast.error('Please select an image first')
      return
    }

    if (!menuName.trim()) {
      toast.error('Please enter a name for this menu')
      return
    }

    setLoading(true)
    try {
      const response = await menuAPI.extractMenu(file, true)
      setResult(response.data)
      
      // Save with name
      if (response.data.validated_items?.length > 0) {
        const items = response.data.validated_items.map(item => ({
          name: item.name,
          price: item.price
        }))
        
        await menuAPI.saveMenu(menuName.trim(), items)
        toast.success(`Menu "${menuName}" saved with ${items.length} items!`)
        loadMenuHistory()
        setMenuName('')
      } else {
        toast.success(`Saved ${response.data.items_saved || 0} food items!`)
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process image')
    }
    setLoading(false)
  }

  const handleDeleteMenu = async (menuId) => {
    if (!confirm('Delete this menu?')) return
    
    try {
      await menuAPI.deleteMenu(menuId)
      toast.success('Menu deleted')
      loadMenuHistory()
    } catch (error) {
      toast.error('Failed to delete menu')
    }
  }

  const handleRenameMenu = async (menuId) => {
    if (!editingName.trim()) return
    
    try {
      await menuAPI.renameMenu(menuId, editingName.trim())
      toast.success('Menu renamed')
      setEditingMenuId(null)
      setEditingName('')
      loadMenuHistory()
    } catch (error) {
      toast.error('Failed to rename menu')
    }
  }

  const viewMenuDetails = async (menuId) => {
    try {
      const response = await menuAPI.getMenuById(menuId)
      setResult({ validated_items: response.data.menu.items })
      setShowHistory(false)
    } catch (error) {
      toast.error('Failed to load menu')
    }
  }

  const clearUpload = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Menu Scanner</h1>
          <p className="text-gray-500 mt-1">Upload a canteen menu image to extract items and prices</p>
        </div>
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="btn-secondary flex items-center space-x-2"
        >
          <FiClock />
          <span>History ({menuHistory.length})</span>
        </button>
      </div>

      {/* Menu History Panel */}
      {showHistory && (
        <div className="card mb-6">
          <h3 className="text-lg font-semibold mb-4">Saved Menus</h3>
          {menuHistory.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No saved menus yet. Scan a menu to get started!</p>
          ) : (
            <div className="space-y-3">
              {menuHistory.map((menu) => (
                <div key={menu.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    {editingMenuId === menu.id ? (
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          className="input-field text-sm"
                          placeholder="Menu name"
                        />
                        <button
                          onClick={() => handleRenameMenu(menu.id)}
                          className="p-1 text-green-600 hover:bg-green-100 rounded"
                        >
                          <FiSave className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditingMenuId(null)}
                          className="p-1 text-gray-600 hover:bg-gray-200 rounded"
                        >
                          <FiX className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <p className="font-medium text-gray-800">{menu.name}</p>
                        <p className="text-sm text-gray-500">
                          {menu.total_items} items • {menu.veg_items} veg • 
                          {new Date(menu.created_at).toLocaleDateString()}
                        </p>
                      </>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => viewMenuDetails(menu.id)}
                      className="p-2 text-blue-600 hover:bg-blue-100 rounded"
                      title="View items"
                    >
                      <FiSearch className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        setEditingMenuId(menu.id)
                        setEditingName(menu.name)
                      }}
                      className="p-2 text-gray-600 hover:bg-gray-200 rounded"
                      title="Rename"
                    >
                      <FiEdit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteMenu(menu.id)}
                      className="p-2 text-red-600 hover:bg-red-100 rounded"
                      title="Delete"
                    >
                      <FiTrash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Upload Area */}
      <div className="card mb-8">
        {!preview ? (
          <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-500 hover:bg-gray-50 transition-colors">
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <FiCamera className="w-12 h-12 text-gray-400 mb-4" />
              <p className="mb-2 text-sm text-gray-500">
                <span className="font-semibold">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-gray-400">PNG, JPG or WEBP (MAX. 10MB)</p>
            </div>
            <input 
              type="file" 
              className="hidden" 
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileChange}
            />
          </label>
        ) : (
          <div className="space-y-4">
            <div className="relative">
              <img 
                src={preview} 
                alt="Menu preview" 
                className="w-full max-h-96 object-contain rounded-lg"
              />
              <button
                onClick={clearUpload}
                className="absolute top-2 right-2 p-2 bg-red-500 text-white rounded-full hover:bg-red-600"
              >
                <FiX className="w-4 h-4" />
              </button>
            </div>
            
            {/* Menu Name Input */}
            <div className="flex items-center space-x-3">
              <input
                type="text"
                value={menuName}
                onChange={(e) => setMenuName(e.target.value)}
                placeholder="Enter menu name (e.g., College Canteen)"
                className="flex-1 input-field"
              />
            </div>
            
            <div className="flex justify-center space-x-3">
              <button
                onClick={handleUpload}
                disabled={loading}
                className="btn-primary flex items-center space-x-2"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <FiUpload />
                    <span>Scan & Save Menu</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Summary */}
          {result.ocr_confidence !== undefined && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Extraction Results</h3>
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-primary-600">{result.items_saved || result.validated_items?.length || 0}</p>
                  <p className="text-sm text-gray-500">Items Saved</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-green-600">{result.ocr_confidence?.toFixed(0) || 0}%</p>
                  <p className="text-sm text-gray-500">OCR Confidence</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-blue-600">
                    {result.validated_items?.filter(i => i.validation_source === 'database').length || 0}
                  </p>
                  <p className="text-sm text-gray-500">DB Matches</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-purple-600">
                    {result.validated_items?.filter(i => i.validation_source === 'ml_prediction').length || 0}
                  </p>
                  <p className="text-sm text-gray-500">ML Predictions</p>
                </div>
              </div>
              {result.message && (
                <p className="mt-4 text-sm text-gray-600 text-center">{result.message}</p>
              )}
            </div>
          )}

          {/* Extracted Items */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Menu Items</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left">Item Name</th>
                    <th className="px-4 py-2 text-left">Price</th>
                    <th className="px-4 py-2 text-left">Calories</th>
                    <th className="px-4 py-2 text-left">Protein</th>
                    <th className="px-4 py-2 text-left">Source</th>
                    <th className="px-4 py-2 text-center">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {result.validated_items?.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium">
                        {item.is_veg !== false && <span className="text-green-600 mr-1">🟢</span>}
                        {item.name}
                      </td>
                      <td className="px-4 py-3">
                        {item.extracted_price || item.price ? `₹${(item.extracted_price || item.price).toFixed(0)}` : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {item.calories ? `${item.calories.toFixed(0)} kcal` : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {item.protein ? `${item.protein.toFixed(1)}g` : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {item.validation_source === 'database' ? (
                          <span className="inline-flex items-center px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs">
                            <FiCheck className="w-3 h-3 mr-1" />
                            Database
                          </span>
                        ) : item.validation_source === 'ml_prediction' ? (
                          <span className="inline-flex items-center px-2 py-1 rounded-full bg-purple-100 text-purple-700 text-xs">
                            <FiSearch className="w-3 h-3 mr-1" />
                            ML Predicted
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-1 rounded-full bg-blue-100 text-blue-700 text-xs">
                            Hybrid
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
                          item.confidence >= 0.85 ? 'bg-green-100 text-green-700' :
                          item.confidence >= 0.7 ? 'bg-yellow-100 text-yellow-700' :
                          'bg-orange-100 text-orange-700'
                        }`}>
                          {(item.confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Nutrition Summary for All Items */}
          {result.validated_items && result.validated_items.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Total Nutrition Summary</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['calories', 'protein', 'carbs', 'fats'].map(nutrient => {
                  const total = result.validated_items.reduce((sum, item) => 
                    sum + (item[nutrient] || 0), 0
                  )
                  return (
                    <div key={nutrient} className="text-center p-4 bg-gray-50 rounded-lg">
                      <p className="text-2xl font-bold text-gray-800">
                        {total.toFixed(0)}{nutrient === 'calories' ? '' : 'g'}
                      </p>
                      <p className="text-sm text-gray-500 capitalize">{nutrient}</p>
                    </div>
                  )
                })}
              </div>
              
              {result.menu_stats && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-2">Menu Statistics</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-blue-800">
                      <span className="font-medium">Veg Items:</span> {result.menu_stats.veg_items}
                    </div>
                    <div className="text-blue-800">
                      <span className="font-medium">Non-Veg:</span> {result.menu_stats.non_veg_items}
                    </div>
                    <div className="text-blue-800">
                      <span className="font-medium">Avg Confidence:</span> {result.menu_stats.avg_confidence}%
                    </div>
                    <div className="text-blue-800">
                      <span className="font-medium">ML Predictions:</span> {result.menu_stats.ml_predictions}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
