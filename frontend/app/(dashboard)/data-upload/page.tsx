"use client"

import { useState, useRef } from "react"
import { Check, AlertCircle, File, Loader2, Upload } from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/app/components/ui/card"
import { PageHeader } from "@/app/components/ui/PageHeader"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { Alert, AlertDescription, AlertTitle } from "@/app/components/ui/alert"
import { CatalogSelect } from "@/app/components/ui/CatalogSelect"
import api, { CsvUploadResponse } from "@/app/services/api"
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
        <CatalogSelect
          catalogField="catalog_type"
          label="Catalog Type (Optional)"
          value={catalogType}
          onValueChange={(value) => setCatalogType(value || "")}
          placeholder="E.g., mysql, postgres, api"
          className="bg-input border-border text-foreground"
          allowCustom={true}
        />
        
        <CatalogSelect
          catalogField="catalog_subtype"
          label="Catalog Subtype (Optional)"
          value={catalogSubtype}
          onValueChange={(value) => setCatalogSubtype(value || "")}
          placeholder="E.g., customer, orders, get"
          className="bg-input border-border text-foreground"
          allowCustom={true}
        />
        
        <CatalogSelect
          catalogField="catalog_name"
          label="Catalog Name (Optional)"
          value={catalogName}
          onValueChange={(value) => setCatalogName(value || "")}
          placeholder="E.g., customer_query, get_orders"
          className="bg-input border-border text-foreground"
          allowCustom={true}
        />
      </div>
    )
  }
  
  return (
    <div className="container mx-auto py-6 space-y-8">
      <PageHeader
        title="Data Upload"
        description="Upload CSV files and import API specifications"
        icon={Upload}
        actions={
          <Button 
            variant="outline" 
            onClick={resetForm}
            className="border-border hover:bg-accent hover:text-accent-foreground text-muted-foreground"
          >
            Reset
          </Button>
        }
      />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground">
              <Upload className="h-5 w-5" />
              CSV Upload
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Upload a CSV file to populate the cache with embeddings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="bg-muted/50 border-border">
              <File className="h-4 w-4 text-muted-foreground" />
              <AlertTitle className="text-foreground">CSV Format</AlertTitle>
              <AlertDescription className="text-muted-foreground">
                Your CSV file must include the columns <code className="text-foreground">nl_query</code> and <code className="text-foreground">template</code>.
                Optional columns: <code className="text-foreground">tags</code>, <code className="text-foreground">reasoning_trace</code>, <code className="text-foreground">is_template</code>, 
                <code className="text-foreground">catalog_type</code>, <code className="text-foreground">catalog_subtype</code>, <code className="text-foreground">catalog_name</code>.
                <br /><br />
                You can also specify default catalog values below, but values in the CSV file will take precedence.
              </AlertDescription>
            </Alert>
            
            <div className="space-y-2">
              <Label htmlFor="template-type" className="text-foreground">Template Type</Label>
              <Select 
                value={templateType} 
                onValueChange={setTemplateType}
              >
                <SelectTrigger id="template-type" className="bg-input border-border text-foreground">
                  <SelectValue placeholder="Select template type" />
                </SelectTrigger>
                <SelectContent className="bg-input border-border text-foreground">
                  <SelectItem value="sql" className="text-foreground">SQL</SelectItem>
                  <SelectItem value="api" className="text-foreground">API</SelectItem>
                  <SelectItem value="url" className="text-foreground">URL</SelectItem>
                  <SelectItem value="workflow" className="text-foreground">Workflow</SelectItem>
                  <SelectItem value="reasoning_steps" className="text-foreground">Reasoning Steps</SelectItem>
                <SelectItem value="dsl" className="text-foreground">DSL Components</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {renderCatalogFields()}
            
            <div className="space-y-2">
              <Label htmlFor="csv-file" className="text-foreground">Select CSV File</Label>
              <Input
                ref={fileInputRef}
                id="csv-file"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="bg-input border-border text-foreground"
              />
              {file && (
                <p className="text-sm text-muted-foreground">
                  Selected file: {file.name} ({Math.round(file.size / 1024)} KB)
                </p>
              )}
            </div>
            
            {error && (
              <div className="p-3 border border-destructive/50 bg-destructive/10 rounded-md text-destructive flex gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <p>{error}</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Button
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
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
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground">
              <Upload className="h-5 w-5" />
              Swagger URL Upload
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Provide a Swagger URL to generate API templates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="bg-input border-border">
              <File className="h-4 w-4 text-muted-foreground" />
              <AlertTitle className="text-foreground">Swagger Processing</AlertTitle>
              <AlertDescription className="text-muted-foreground">
                Only GET, PUT, and POST operations will be processed into API templates.
                <br /><br />
                You can specify catalog values below to categorize all entries. By default, catalog_type will be 'api', 
                catalog_subtype will be the HTTP method (get, post, put), and catalog_name will be the operationId.
              </AlertDescription>
            </Alert>
            
            <div className="space-y-2">
              <Label htmlFor="swagger-url" className="text-foreground">Swagger URL</Label>
              <Input
                id="swagger-url"
                type="url"
                placeholder="https://api.example.com/swagger.json"
                value={swaggerUrl}
                onChange={(e) => setSwaggerUrl(e.target.value)}
                className="bg-input border-border text-foreground placeholder:text-muted-foreground"
              />
            </div>
            
            {renderCatalogFields()}
            
            {swaggerError && (
              <div className="p-3 border border-destructive/50 bg-destructive/10 rounded-md text-destructive flex gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <p>{swaggerError}</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Button
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
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
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader>
            <CardTitle className="text-foreground">Results</CardTitle>
            <CardDescription className="text-muted-foreground">
              Results of your CSV or Swagger upload
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isUploading && (
              <div className="flex flex-col items-center justify-center h-60 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mb-2" />
                <p>Processing your file...</p>
              </div>
            )}
            
            {!isUploading && !uploadResult && !error && (
              <div className="flex flex-col items-center justify-center h-60 text-muted-foreground">
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
                <div className="rounded-md border border-border bg-input p-4 overflow-auto max-h-[300px]">
                  <div className="grid grid-cols-2 gap-y-2">
                    <div className="text-sm font-medium text-foreground">Total Entries</div>
                    <div className="text-sm text-foreground">{uploadResult.processed + uploadResult.failed}</div>
                    
                    <div className="text-sm font-medium text-foreground">Successful</div>
                    <div className="text-sm text-foreground">{uploadResult.processed}</div>
                    
                    <div className="text-sm font-medium text-foreground">Failed</div>
                    <div className="text-sm text-foreground">{uploadResult.failed}</div>
                  </div>
                </div>
                
                <div className="mt-4 text-sm text-muted-foreground">
                  Successfully processed {uploadResult.processed} of {uploadResult.processed + uploadResult.failed} entries.
                </div>
                
                <div className="flex justify-end space-x-3 mt-4">
                  <Button 
                    variant="outline" 
                    onClick={resetForm}
                    className="border-border hover:bg-input hover:text-foreground text-foreground"
                  >
                    Reset
                  </Button>
                  <Button 
                    onClick={() => router.push('/cache-entries')}
                    className="bg-primary hover:bg-primary/90 text-primary-foreground"
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