import { useState, useRef } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Upload as UploadIcon, File as FileIcon, Loader2, Check, AlertCircle } from "lucide-react";
import api from "@/services/api";

export default function DataUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [templateType, setTemplateType] = useState<string>("sql");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [swaggerUrl, setSwaggerUrl] = useState<string>("");
  const [isSwaggerUploading, setIsSwaggerUploading] = useState(false);
  const [swaggerError, setSwaggerError] = useState<string | null>(null);
  const [catalogType, setCatalogType] = useState<string>("");
  const [catalogSubtype, setCatalogSubtype] = useState<string>("");
  const [catalogName, setCatalogName] = useState<string>("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type !== "text/csv" && !selectedFile.name.endsWith('.csv')) {
        setError("Please select a CSV file");
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file to upload");
      return;
    }
    setIsUploading(true);
    setError(null);
    try {
      const result = await api.uploadCsv(
        file,
        templateType,
        catalogType || undefined,
        catalogSubtype || undefined,
        catalogName || undefined
      );
      setUploadResult(result);
    } catch (err: any) {
      setError(err.message || "An error occurred during upload");
      setUploadResult(null);
    } finally {
      setIsUploading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setUploadResult(null);
    setError(null);
    setCatalogType("");
    setCatalogSubtype("");
    setCatalogName("");
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSwaggerUpload = async () => {
    if (!swaggerUrl) {
      setSwaggerError("Please enter a Swagger URL");
      return;
    }
    setIsSwaggerUploading(true);
    setSwaggerError(null);
    try {
      const result = await api.uploadSwagger(
        swaggerUrl,
        templateType,
        catalogType || undefined,
        catalogSubtype || undefined,
        catalogName || undefined
      );
      setUploadResult(result);
    } catch (err: any) {
      setSwaggerError(err.message || "An error occurred during Swagger upload");
      setUploadResult(null);
    } finally {
      setIsSwaggerUploading(false);
    }
  };

  const renderCatalogFields = () => (
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
  );

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
              <UploadIcon className="h-5 w-5" />
              CSV Upload
            </CardTitle>
            <CardDescription className="text-neutral-400">
              Upload a CSV file to populate the cache with embeddings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="bg-neutral-800 border-neutral-700">
              <FileIcon className="h-4 w-4 text-neutral-400" />
              <AlertTitle className="text-neutral-300">CSV Format</AlertTitle>
              <AlertDescription className="text-neutral-400">
                Your CSV file must include the columns <code className="text-neutral-300">nl_query</code> and <code className="text-neutral-300">template</code>.<br />
                Optional columns: <code className="text-neutral-300">tags</code>, <code className="text-neutral-300">reasoning_trace</code>, <code className="text-neutral-300">is_template</code>, 
                <code className="text-neutral-300">catalog_type</code>, <code className="text-neutral-300">catalog_subtype</code>, <code className="text-neutral-300">catalog_name</code>.<br /><br />
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
              <Label htmlFor="csv-file" className="text-neutral-300">CSV File</Label>
              <Input
                id="csv-file"
                type="file"
                accept=".csv,text/csv"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="bg-neutral-800 border-neutral-700 text-neutral-300"
              />
            </div>
            {error && <Alert className="bg-red-900 border-red-700 text-red-200 flex items-center gap-2"><AlertCircle className="h-4 w-4" />{error}</Alert>}
            <Button
              onClick={handleUpload}
              disabled={isUploading || !file}
              className="w-full bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white font-semibold"
            >
              {isUploading ? <Loader2 className="animate-spin h-5 w-5 mr-2 inline" /> : <UploadIcon className="h-5 w-5 mr-2 inline" />}
              Upload CSV
            </Button>
            {uploadResult && (
              <Alert className="bg-green-900 border-green-700 text-green-200 mt-4">
                <Check className="h-4 w-4" />
                <AlertTitle>Upload Successful</AlertTitle>
                <AlertDescription>
                  {uploadResult.message || "CSV uploaded successfully!"}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-neutral-200">
              <UploadIcon className="h-5 w-5" />
              Swagger Upload
            </CardTitle>
            <CardDescription className="text-neutral-400">
              Upload Swagger documentation by URL to populate the cache
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="swagger-url" className="text-neutral-300">Swagger URL</Label>
              <Input
                id="swagger-url"
                type="url"
                placeholder="https://example.com/swagger.json"
                value={swaggerUrl}
                onChange={e => setSwaggerUrl(e.target.value)}
                className="bg-neutral-800 border-neutral-700 text-neutral-300"
              />
            </div>
            {renderCatalogFields()}
            {swaggerError && <Alert className="bg-red-900 border-red-700 text-red-200 flex items-center gap-2"><AlertCircle className="h-4 w-4" />{swaggerError}</Alert>}
            <Button
              onClick={handleSwaggerUpload}
              disabled={isSwaggerUploading || !swaggerUrl}
              className="w-full bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white font-semibold"
            >
              {isSwaggerUploading ? <Loader2 className="animate-spin h-5 w-5 mr-2 inline" /> : <UploadIcon className="h-5 w-5 mr-2 inline" />}
              Upload Swagger
            </Button>
            {uploadResult && (
              <Alert className="bg-green-900 border-green-700 text-green-200 mt-4">
                <Check className="h-4 w-4" />
                <AlertTitle>Upload Successful</AlertTitle>
                <AlertDescription>
                  {uploadResult.message || "Swagger uploaded successfully!"}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 