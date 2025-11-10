import { useState } from 'react';
import axios from 'axios';
import { Upload, FileText, Briefcase, MessageSquare } from 'lucide-react';
import { useChatContext } from '@/context/ChatContext';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

export const InitialForm = () => {
  const { setThreadId, setCurrentResume, setJobDescription, addMessage, setIsLoading, isLoading } = useChatContext();
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState('');
  const [userMessage, setUserMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!resumeFile || !jdText.trim() || !userMessage.trim()) {
      toast.error('Please fill in all fields');
      return;
    }

    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', resumeFile);
      formData.append('job_description', jdText);
      formData.append('user_message', userMessage);

      const response = await axios.post('http://localhost:8000/optimize_resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setThreadId(response.data.thread_id);
      setCurrentResume(resumeFile);
      setJobDescription(jdText);

      // Push user message first
      addMessage({ role: 'user', content: userMessage });

      // Push AI message with meta (thinking/tools)
      addMessage({
        role: 'ai',
        content: response.data.ai_response,
        meta: {
          tool_used: response.data.tool_used,
          tool_trace: response.data.tool_trace,
          thinking_note: response.data.thinking_note ?? null,
        },
      });

      toast.success('Resume optimization started!');
    } catch (error: any) {
      console.error('Error:', error);
      toast.error(error.response?.data?.detail || 'Failed to start optimization');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="w-full max-w-2xl space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold">Resume Optimizer AI</h1>
          <p className="text-muted-foreground">Upload your resume and job description to get started</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium">
              <FileText className="h-4 w-4" />
              Resume (PDF)
            </label>
            <div className="relative">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                className="hidden"
                id="resume-upload"
              />
              <label
                htmlFor="resume-upload"
                className="flex items-center justify-center gap-2 w-full p-4 border-2 border-dashed border-input rounded-lg cursor-pointer hover:border-primary transition-colors bg-card"
              >
                <Upload className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm">
                  {resumeFile ? resumeFile.name : 'Click to upload PDF'}
                </span>
              </label>
            </div>
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium">
              <Briefcase className="h-4 w-4" />
              Job Description
            </label>
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste the job description here..."
              className="w-full h-32 p-3 bg-card border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium">
              <MessageSquare className="h-4 w-4" />
              Your Message
            </label>
            <textarea
              value={userMessage}
              onChange={(e) => setUserMessage(e.target.value)}
              placeholder="e.g., 'Optimize my resume for this job' or 'Help me tailor my experience section'"
              className="w-full h-24 p-3 bg-card border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full h-12 text-base bg-primary hover:bg-primary/90"
          >
            {isLoading ? 'Processing...' : 'Start Optimization'}
          </Button>
        </form>
      </div>
    </div>
  );
};
