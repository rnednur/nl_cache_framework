"use client"

import { useState, useRef } from "react"
import { Check, CircleAlert, File, Loader2, Upload } from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select"
import { Alert, AlertDescription, AlertTitle } from "../../components/ui/alert"
import api, { CsvUploadResponse } from "../../services/api"
import { useRouter } from "next/navigation"

export default function DataUploadPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [templateType, setTemplateType] = useState<string>("sql")
  const [isUploading, setIsUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<CsvUploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0]
      if (selectedFile.type !== "text/csv" && !selectedFile.name.endsWith('.csv')) {
        setError("Please select a CSV file")
        setFile(null)
        return
      }
      
      setFile(selectedFile)
      setError(null)
    }
  }
  
  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file to upload")
      return
    }
    
    setIsUploading(true)
    setError(null)
    
    try {
      const result = await api.uploadCsv(file, templateType)
      setUploadResult(result)
    } catch (err: any) {
      setError(err.message || "An error occurred during upload")
      setUploadResult(null)
    } finally {
      setIsUploading(false)
    }
  }
  
  const resetForm = () => {
    setFile(null)
    setUploadResult(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }
  
  return (
    <div className="container mx-auto py-6 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Data Upload</h1>
        <Button 
          variant="outline" 
          onClick={resetForm}
        >
          Reset
        </Button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              CSV Upload
            </CardTitle>
            <CardDescription>
              Upload a CSV file to populate the cache with embeddings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <File className="h-4 w-4" />
              <AlertTitle>CSV Format</AlertTitle>
              <AlertDescription>
                Your CSV file must include the columns <code>nl_query</code> and <code>template</code>.
                Optional columns: <code>tags</code>, <code>reasoning_trace</code>, <code>is_template</code>, 
                <code>catalog_type</code>, <code>catalog_subtype</code>, <code>catalog_name</code>.
              </AlertDescription>
            </Alert>
            
            <div className="space-y-2">
              <Label htmlFor="template-type">Template Type</Label>
              <Select 
                value={templateType} 
                onValueChange={setTemplateType}
              >
                <SelectTrigger id="template-type">
                  <SelectValue placeholder="Select template type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sql">SQL</SelectItem>
                  <SelectItem value="api">API</SelectItem>
                  <SelectItem value="url">URL</SelectItem>
                  <SelectItem value="workflow">Workflow</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="csv-file">Select CSV File</Label>
              <Input
                ref={fileInputRef}
                id="csv-file"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
              />
              {file && (
                <p className="text-sm text-slate-600">
                  Selected file: {file.name} ({Math.round(file.size / 1024)} KB)
                </p>
              )}
            </div>
            
            {error && (
              <div className="p-3 border border-red-200 bg-red-50 rounded-md text-red-700 flex gap-2">
                <CircleAlert className="h-5 w-5 flex-shrink-0" />
                <p>{error}</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Button
              className="w-full"
              onClick={handleUpload}
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : "Upload CSV"}
            </Button>
          </CardFooter>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
            <CardDescription>
              Results of your CSV upload
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isUploading && (
              <div className="flex flex-col items-center justify-center h-60 text-slate-500">
                <Loader2 className="h-8 w-8 animate-spin mb-2" />
                <p>Processing your file...</p>
              </div>
            )}
            
            {!isUploading && !uploadResult && !error && (
              <div className="flex flex-col items-center justify-center h-60 text-slate-500">
                <Upload className="h-8 w-8 mb-2" />
                <p>Upload a file to see results</p>
              </div>
            )}
            
            {!isUploading && uploadResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 border border-green-100 bg-green-50 rounded-md text-green-800">
                    <p className="text-lg font-semibold">{uploadResult.processed}</p>
                    <p className="text-sm">Entries processed</p>
                  </div>
                  
                  <div className="p-4 border border-red-100 bg-red-50 rounded-md text-red-800">
                    <p className="text-lg font-semibold">{uploadResult.failed}</p>
                    <p className="text-sm">Failed entries</p>
                  </div>
                </div>
                
                <div className="border rounded-md overflow-hidden">
                  <div className="p-3 bg-slate-100 font-medium border-b">
                    Upload Results
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {uploadResult.results.map((result, index) => (
                      <div 
                        key={index}
                        className={`p-3 border-b flex items-start gap-2 ${
                          index % 2 === 0 ? 'bg-white' : 'bg-slate-50'
                        } ${
                          result.status === 'error' ? 'text-red-700' : 'text-slate-800'
                        }`}
                      >
                        {result.status === 'success' ? (
                          <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                        ) : (
                          <CircleAlert className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className="text-sm font-medium truncate max-w-md">
                            {result.nl_query}
                          </p>
                          {result.error && (
                            <p className="text-xs text-red-600 mt-1">{result.error}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="flex justify-between pt-2">
                  <Button
                    variant="outline"
                    onClick={resetForm}
                  >
                    Upload Another File
                  </Button>
                  
                  <Button
                    onClick={() => router.push('/complete-test')}
                  >
                    Go to Complete Test
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 