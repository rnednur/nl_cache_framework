"use client"

import { useState, useRef } from "react"
import { Check, AlertCircle, File, Loader2, Upload } from "lucide-react"
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
  const [swaggerUrl, setSwaggerUrl] = useState<string>("")
  const [isSwaggerUploading, setIsSwaggerUploading] = useState(false)
  const [swaggerError, setSwaggerError] = useState<string | null>(null)
  
  // Add catalog fields for both CSV and Swagger uploads
  const [catalogType, setCatalogType] = useState<string>("")
  const [catalogSubtype, setCatalogSubtype] = useState<string>("")
  const [catalogName, setCatalogName] = useState<string>("")
  
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
      const result = await api.uploadCsv(
        file, 
        templateType,
        catalogType || undefined,
        catalogSubtype || undefined,
        catalogName || undefined
      )
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
    setCatalogType("")
    setCatalogSubtype("")
    setCatalogName("")
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }
  
  const handleSwaggerUpload = async () => {
    if (!swaggerUrl) {
      setSwaggerError("Please enter a Swagger URL")
      return
    }
    
    setIsSwaggerUploading(true)
    setSwaggerError(null)
    
    try {
      const result = await api.uploadSwagger(
        swaggerUrl, 
        templateType, 
        catalogType || undefined,
        catalogSubtype || undefined,
        catalogName || undefined
      )
      setUploadResult(result)
    } catch (err: any) {
      setSwaggerError(err.message || "An error occurred during Swagger upload")
      setUploadResult(null)
    } finally {
      setIsSwaggerUploading(false)
    }
  }
  
  // Helper function to render catalog fields
  const renderCatalogFields = () => {
    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="catalog-type" className="text-neutral-300">Catalog Type (Optional)</Label>
          <Input
            id="catalog-type"
            placeholder="E.g., mysql, postgres, api"
            value={catalogType}
            onChange={(e) => setCatalogType(e.target.value)}
            className="bg-neutral-800 border-neutral-700 text-neutral-300 placeholder:text-neutral-500"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="catalog-subtype" className="text-neutral-300">Catalog Subtype (Optional)</Label>
          <Input
            id="catalog-subtype"
            placeholder="E.g., customer, orders, get"
            value={catalogSubtype}
            onChange={(e) => setCatalogSubtype(e.target.value)}
            className="bg-neutral-800 border-neutral-700 text-neutral-300 placeholder:text-neutral-500"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="catalog-name" className="text-neutral-300">Catalog Name (Optional)</Label>
          <Input
            id="catalog-name"
            placeholder="E.g., customer_query, get_orders"
            value={catalogName}
            onChange={(e) => setCatalogName(e.target.value)}
            className="bg-neutral-800 border-neutral-700 text-neutral-300 placeholder:text-neutral-500"
          />
        </div>
      </div>
    )
  }
  
  return (
    <div className="container mx-auto py-6 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-neutral-200">Data Upload</h1>
        <Button 
          variant="outline" 
          onClick={resetForm}
          className="border-neutral-700 hover:bg-neutral-800 hover:text-neutral-200 text-neutral-300"
        >
          Reset
        </Button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-neutral-200">
              <Upload className="h-5 w-5" />
              CSV Upload
            </CardTitle>
            <CardDescription className="text-neutral-400">
              Upload a CSV file to populate the cache with embeddings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="bg-neutral-800 border-neutral-700">
              <File className="h-4 w-4 text-neutral-400" />
              <AlertTitle className="text-neutral-300">CSV Format</AlertTitle>
              <AlertDescription className="text-neutral-400">
                Your CSV file must include the columns <code className="text-neutral-300">nl_query</code> and <code className="text-neutral-300">template</code>.
                Optional columns: <code className="text-neutral-300">tags</code>, <code className="text-neutral-300">reasoning_trace</code>, <code className="text-neutral-300">is_template</code>, 
                <code className="text-neutral-300">catalog_type</code>, <code className="text-neutral-300">catalog_subtype</code>, <code className="text-neutral-300">catalog_name</code>.
                <br /><br />
                You can also specify default catalog values below, but values in the CSV file will take precedence.
              </AlertDescription>
            </Alert>
            
            <div className="space-y-2">
              <Label htmlFor="template-type" className="text-neutral-300">Template Type</Label>
              <Select 
                value={templateType} 
                onValueChange={setTemplateType}
              >
                <SelectTrigger id="template-type" className="bg-neutral-800 border-neutral-700 text-neutral-300">
                  <SelectValue placeholder="Select template type" />
                </SelectTrigger>
                <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                  <SelectItem value="sql" className="text-neutral-300">SQL</SelectItem>
                  <SelectItem value="api" className="text-neutral-300">API</SelectItem>
                  <SelectItem value="url" className="text-neutral-300">URL</SelectItem>
                  <SelectItem value="workflow" className="text-neutral-300">Workflow</SelectItem>
                  <SelectItem value="reasoning_steps" className="text-neutral-300">Reasoning Steps</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {renderCatalogFields()}
            
            <div className="space-y-2">
              <Label htmlFor="csv-file" className="text-neutral-300">Select CSV File</Label>
              <Input
                ref={fileInputRef}
                id="csv-file"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="bg-neutral-800 border-neutral-700 text-neutral-300"
              />
              {file && (
                <p className="text-sm text-neutral-400">
                  Selected file: {file.name} ({Math.round(file.size / 1024)} KB)
                </p>
              )}
            </div>
            
            {error && (
              <div className="p-3 border border-red-700 bg-red-900/30 rounded-md text-red-300 flex gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <p>{error}</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Button
              className="w-full bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white"
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
        
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-neutral-200">
              <Upload className="h-5 w-5" />
              Swagger URL Upload
            </CardTitle>
            <CardDescription className="text-neutral-400">
              Provide a Swagger URL to generate API templates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="bg-neutral-800 border-neutral-700">
              <File className="h-4 w-4 text-neutral-400" />
              <AlertTitle className="text-neutral-300">Swagger Processing</AlertTitle>
              <AlertDescription className="text-neutral-400">
                Only GET, PUT, and POST operations will be processed into API templates.
                <br /><br />
                You can specify catalog values below to categorize all entries. By default, catalog_type will be 'api', 
                catalog_subtype will be the HTTP method (get, post, put), and catalog_name will be the operationId.
              </AlertDescription>
            </Alert>
            
            <div className="space-y-2">
              <Label htmlFor="swagger-url" className="text-neutral-300">Swagger URL</Label>
              <Input
                id="swagger-url"
                type="url"
                placeholder="https://api.example.com/swagger.json"
                value={swaggerUrl}
                onChange={(e) => setSwaggerUrl(e.target.value)}
                className="bg-neutral-800 border-neutral-700 text-neutral-300 placeholder:text-neutral-500"
              />
            </div>
            
            {renderCatalogFields()}
            
            {swaggerError && (
              <div className="p-3 border border-red-700 bg-red-900/30 rounded-md text-red-300 flex gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <p>{swaggerError}</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Button
              className="w-full bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white"
              onClick={handleSwaggerUpload}
              disabled={!swaggerUrl || isSwaggerUploading}
            >
              {isSwaggerUploading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing Swagger URL... This may take a while.
                </>
              ) : "Process Swagger URL"}
            </Button>
          </CardFooter>
        </Card>
        
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader>
            <CardTitle className="text-neutral-200">Results</CardTitle>
            <CardDescription className="text-neutral-400">
              Results of your CSV or Swagger upload
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isUploading && (
              <div className="flex flex-col items-center justify-center h-60 text-neutral-400">
                <Loader2 className="h-8 w-8 animate-spin mb-2" />
                <p>Processing your file...</p>
              </div>
            )}
            
            {!isUploading && !uploadResult && !error && (
              <div className="flex flex-col items-center justify-center h-60 text-neutral-500">
                <Upload className="h-16 w-16 mb-2" />
                <p>Upload a file to see the results</p>
              </div>
            )}
            
            {uploadResult && !isUploading && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-green-500 mb-4">
                  <Check className="h-5 w-5" />
                  <h3 className="font-medium">Upload successful!</h3>
                </div>
                <div className="rounded-md border border-neutral-700 bg-neutral-800 p-4 overflow-auto max-h-[300px]">
                  <div className="grid grid-cols-2 gap-y-2">
                    <div className="text-sm font-medium text-neutral-300">Total Entries</div>
                    <div className="text-sm text-neutral-200">{uploadResult.processed + uploadResult.failed}</div>
                    
                    <div className="text-sm font-medium text-neutral-300">Successful</div>
                    <div className="text-sm text-neutral-200">{uploadResult.processed}</div>
                    
                    <div className="text-sm font-medium text-neutral-300">Failed</div>
                    <div className="text-sm text-neutral-200">{uploadResult.failed}</div>
                  </div>
                </div>
                
                <div className="mt-4 text-sm text-neutral-400">
                  Successfully processed {uploadResult.processed} of {uploadResult.processed + uploadResult.failed} entries.
                </div>
                
                <div className="flex justify-end space-x-3 mt-4">
                  <Button 
                    variant="outline" 
                    onClick={resetForm}
                    className="border-neutral-700 hover:bg-neutral-800 hover:text-neutral-200 text-neutral-300"
                  >
                    Reset
                  </Button>
                  <Button 
                    onClick={() => router.push('/cache-entries')}
                    className="bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white"
                  >
                    View Cache Entries
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