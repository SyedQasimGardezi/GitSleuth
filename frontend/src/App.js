import React, { useState, useEffect } from 'react';
import { Search, Github, Loader2, CheckCircle, AlertCircle, MessageSquare } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [confidence, setConfidence] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);

  // Poll for status updates
  useEffect(() => {
    if (sessionId && status?.status === 'indexing') {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/status/${sessionId}`);
          setStatus(response.data);
        } catch (error) {
          console.error('Error fetching status:', error);
        }
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [sessionId, status?.status]);

  const handleIndexRepo = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setIsLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/index`, {
        repo_url: repoUrl.trim()
      });
      
      setSessionId(response.data.session_id);
      setStatus({ status: 'indexing', message: 'Repository indexing started...', progress: 0 });
      setAnswer('');
      setSources([]);
      setConfidence('');
      setConversationId(null);
      setConversationHistory([]);
    } catch (error) {
      console.error('Error indexing repository:', error);
      alert('Error indexing repository. Please check the URL and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!question.trim() || !sessionId) return;

    setIsQuerying(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/query`, {
        session_id: sessionId,
        question: question.trim(),
        conversation_history: conversationHistory
      });
      
      setAnswer(response.data.answer);
      setSources(response.data.sources);
      setConfidence(response.data.confidence);
      setConversationId(response.data.conversation_id);
      
      // Update conversation history
      const newHistory = [
        ...conversationHistory,
        { role: 'user', content: question.trim() },
        { role: 'assistant', content: response.data.answer, confidence: response.data.confidence }
      ];
      setConversationHistory(newHistory);
      
      setQuestion('');
    } catch (error) {
      console.error('Error querying repository:', error);
      alert('Error querying repository. Please try again.');
    } finally {
      setIsQuerying(false);
    }
  };

  const getStatusIcon = () => {
    if (!status) return null;
    
    switch (status.status) {
      case 'indexing':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />;
      case 'ready':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    if (!status) return 'text-gray-500';
    
    switch (status.status) {
      case 'indexing':
        return 'text-blue-500';
      case 'ready':
        return 'text-green-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'high':
        return 'text-green-600 bg-green-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'low':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const clearConversation = () => {
    setConversationHistory([]);
    setAnswer('');
    setSources([]);
    setConfidence('');
    if (conversationId) {
      // Clear conversation on backend
      axios.delete(`${API_BASE_URL}/conversation/${conversationId}`)
        .catch(error => console.error('Error clearing conversation:', error));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <Github className="w-8 h-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-900">GitSleuth</h1>
            </div>
            <p className="text-sm text-gray-500">AI-powered GitHub repository analyzer</p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Repository Input Section */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Index Repository</h2>
          <form onSubmit={handleIndexRepo} className="space-y-4">
            <div>
              <label htmlFor="repoUrl" className="block text-sm font-medium text-gray-700 mb-2">
                GitHub Repository URL
              </label>
              <div className="flex space-x-4">
                <input
                  type="url"
                  id="repoUrl"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/username/repository"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                  required
                />
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Search className="w-4 h-4" />
                  )}
                  <span>{isLoading ? 'Indexing...' : 'Index'}</span>
                </button>
              </div>
            </div>
          </form>

          {/* Status Display */}
          {status && (
            <div className="mt-4 p-4 bg-gray-50 rounded-md">
              <div className="flex items-center space-x-3">
                {getStatusIcon()}
                <div className="flex-1">
                  <p className={`text-sm font-medium ${getStatusColor()}`}>
                    {status.message}
                  </p>
                  {status.progress !== undefined && status.status === 'indexing' && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${status.progress}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{status.progress}% complete</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Query Section */}
        {status?.status === 'ready' && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                <MessageSquare className="w-5 h-5" />
                <span>Ask Questions</span>
              </h2>
              {conversationHistory.length > 0 && (
                <button
                  onClick={clearConversation}
                  className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Clear Conversation
                </button>
              )}
            </div>
            
            <form onSubmit={handleQuery} className="space-y-4">
              <div>
                <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
                  Ask a question about the codebase
                </label>
                <div className="flex space-x-4">
                  <input
                    type="text"
                    id="question"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="e.g., Where is authentication logic handled?"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    required
                  />
                  <button
                    type="submit"
                    disabled={isQuerying}
                    className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {isQuerying ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Search className="w-4 h-4" />
                    )}
                    <span>{isQuerying ? 'Thinking...' : 'Ask'}</span>
                  </button>
                </div>
              </div>
            </form>

            {/* Conversation History */}
            {conversationHistory.length > 0 && (
              <div className="mt-6">
                <h3 className="text-md font-semibold text-gray-900 mb-3">Conversation History</h3>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {conversationHistory.map((message, index) => (
                    <div key={index} className={`p-4 rounded-md ${
                      message.role === 'user' 
                        ? 'bg-blue-50 border-l-4 border-blue-400' 
                        : 'bg-gray-50 border-l-4 border-gray-400'
                    }`}>
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-sm font-medium text-gray-700">
                          {message.role === 'user' ? 'You' : 'GitSleuth'}
                        </span>
                        {message.confidence && (
                          <span className={`px-2 py-1 text-xs rounded-full ${getConfidenceColor(message.confidence)}`}>
                            {message.confidence} confidence
                          </span>
                        )}
                      </div>
                      <p className="text-gray-800 whitespace-pre-wrap">{message.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Current Answer Display */}
            {answer && (
              <div className="mt-6">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-md font-semibold text-gray-900">Latest Answer</h3>
                  {confidence && (
                    <span className={`px-3 py-1 text-sm rounded-full ${getConfidenceColor(confidence)}`}>
                      {confidence} confidence
                    </span>
                  )}
                </div>
                <div className="bg-gray-50 rounded-md p-4">
                  <p className="text-gray-800 whitespace-pre-wrap">{answer}</p>
                </div>

                {/* Sources */}
                {sources.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">Sources</h4>
                    <div className="space-y-2">
                      {sources.map((source, index) => (
                        <div key={index} className="bg-white border rounded-md p-3">
                          <p className="text-sm font-medium text-primary-600 mb-1">
                            {source.file}
                            {source.line_number && ` (line ${source.line_number})`}
                          </p>
                          <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded font-mono">
                            {source.snippet}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
