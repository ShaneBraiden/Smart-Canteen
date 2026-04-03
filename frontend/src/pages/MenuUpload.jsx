import { useState } from 'react'
import { menuAPI } from '../services/api'
import toast from 'react-hot-toast'
import { FiUpload, FiCamera, FiCheck, FiX, FiSearch } from 'react-icons/fi'

export default function MenuUpload() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

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

    setLoading(true)
    try {
      const response = await menuAPI.extractMenu(file)
      setResult(response.data)
      toast.success(`Found ${response.data.items_found} items!`)
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process image')
    }
    setLoading(false)
  }

  const clearUpload = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Menu Scanner</h1>
        <p className="text-gray-500 mt-1">Upload a canteen menu image to extract items and prices</p>
      </div>

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
            <div className="flex justify-center">
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
                    <FiSearch />
                    <span>Extract Menu Items</span>
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
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Extraction Results</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-primary-600">{result.items_found}</p>
                <p className="text-sm text-gray-500">Items Found</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">{result.ocr_confidence.toFixed(0)}%</p>
                <p className="text-sm text-gray-500">OCR Confidence</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-blue-600">
                  {result.mapped_items.filter(i => i.matched_name).length}
                </p>
                <p className="text-sm text-gray-500">Matched in Database</p>
              </div>
            </div>
          </div>

          {/* Extracted Items */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Extracted Items</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left">Extracted Name</th>
                    <th className="px-4 py-2 text-left">Price</th>
                    <th className="px-4 py-2 text-left">Matched Item</th>
                    <th className="px-4 py-2 text-left">Calories</th>
                    <th className="px-4 py-2 text-center">Match</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {result.mapped_items.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3">{item.extracted_name}</td>
                      <td className="px-4 py-3">
                        {item.extracted_price ? `₹${item.extracted_price}` : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {item.matched_name || (
                          <span className="text-gray-400">No match</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {item.nutrition?.calories ? `${item.nutrition.calories} kcal` : '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {item.matched_name ? (
                          <span className="inline-flex items-center px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs">
                            <FiCheck className="w-3 h-3 mr-1" />
                            {(item.match_confidence * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-1 rounded-full bg-gray-100 text-gray-500 text-xs">
                            <FiX className="w-3 h-3 mr-1" />
                            N/A
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Nutrition Summary for Matched Items */}
          {result.mapped_items.some(i => i.nutrition) && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Nutrition Summary (Matched Items)</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['calories', 'protein', 'carbs', 'fats'].map(nutrient => {
                  const total = result.mapped_items.reduce((sum, item) => 
                    sum + (item.nutrition?.[nutrient] || 0), 0
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
            </div>
          )}
        </div>
      )}
    </div>
  )
}
