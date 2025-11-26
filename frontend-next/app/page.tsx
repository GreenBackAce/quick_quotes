import { AudioUploader } from '@/components/AudioUploader';

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">AI Meeting Transcription</h1>
        <p className="text-lg text-muted-foreground">
          Upload your audio file and get an accurate transcript with speaker diarization
        </p>
      </div>

      <AudioUploader />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
        <div className="text-center space-y-2">
          <div className="text-3xl">⚡</div>
          <h3 className="font-semibold">Fast Processing</h3>
          <p className="text-sm text-muted-foreground">
            2 minutes for an 8-minute audio file
          </p>
        </div>
        <div className="text-center space-y-2">
          <div className="text-3xl">🎯</div>
          <h3 className="font-semibold">Accurate Diarization</h3>
          <p className="text-sm text-muted-foreground">
            Automatically detect and label different speakers
          </p>
        </div>
        <div className="text-center space-y-2">
          <div className="text-3xl">📝</div>
          <h3 className="font-semibold">Easy Export</h3>
          <p className="text-sm text-muted-foreground">
            Download your transcript in multiple formats
          </p>
        </div>
      </div>
    </div>
  );
}
