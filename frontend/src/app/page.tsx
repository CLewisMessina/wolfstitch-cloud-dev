// frontend/src/app/page.tsx
// Updated download functionality for page.tsx
// Replace the existing downloadResults function with this implementation:

const downloadResults = async () => {
  if (!selectedFiles[0]) return;
  
  try {
    setProcessingStep('processing');
    setProgress(0);
    setError(null);
    
    // Create FormData with the file
    const formData = new FormData();
    formData.append('file', selectedFiles[0]);
    formData.append('tokenizer', 'gpt-4');
    formData.append('max_tokens', '1000');
    formData.append('chunk_method', 'paragraph');
    formData.append('preserve_structure', 'true');
    formData.append('export_format', 'jsonl');
    
    // Call the full processing endpoint
    const response = await fetch(`${API_URL}/api/v1/process-full`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Processing failed');
    }
    
    const result = await response.json();
    const jobId = result.job_id;
    
    console.log('Full processing started:', jobId);
    
    // Poll for job status
    let jobComplete = false;
    let downloadUrl = null;
    
    while (!jobComplete) {
      await new Promise(resolve => setTimeout(resolve, 1000)); // Poll every second
      
      const statusResponse = await fetch(`${API_URL}/api/v1/jobs/${jobId}/status`);
      if (!statusResponse.ok) {
        throw new Error('Failed to check job status');
      }
      
      const status = await statusResponse.json();
      
      // Update progress
      setProgress(status.progress || 0);
      
      if (status.status === 'completed') {
        jobComplete = true;
        downloadUrl = status.download_url;
        console.log('Processing completed:', status);
      } else if (status.status === 'failed') {
        throw new Error(status.error || 'Processing failed');
      }
    }
    
    if (downloadUrl) {
      // Download the file
      console.log('Downloading from:', downloadUrl);
      
      // For development, construct full URL if needed
      const fullDownloadUrl = downloadUrl.startsWith('http') 
        ? downloadUrl 
        : `${API_URL}${downloadUrl}`;
      
      // Create a temporary anchor element to trigger download
      const link = document.createElement('a');
      link.href = fullDownloadUrl;
      link.download = selectedFiles[0].name.replace(/\.[^/.]+$/, '') + '_processed.jsonl';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      setProcessingStep('complete');
      setProgress(100);
      console.log('Download initiated successfully');
    }
    
  } catch (error) {
    console.error('Download error:', error);
    setError(error instanceof Error ? error.message : 'Download failed');
    setProcessingStep('error');
  }
};

// Also update the UI to show progress during full processing
// In the processing step section of your render, add:

{processingStep === 'processing' && (
  <div className="space-y-4">
    <div className="flex items-center space-x-3">
      <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
      <p className="text-lg font-medium text-gray-900">
        Processing your file...
      </p>
    </div>
    
    <div className="w-full bg-gray-200 rounded-full h-2.5">
      <div 
        className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
        style={{ width: `${progress}%` }}
      />
    </div>
    
    <p className="text-sm text-gray-600">
      {progress < 20 && "Uploading file..."}
      {progress >= 20 && progress < 70 && "Processing chunks..."}
      {progress >= 70 && progress < 90 && "Generating export..."}
      {progress >= 90 && "Finalizing download..."}
    </p>
  </div>
)}