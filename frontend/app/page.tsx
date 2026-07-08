import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-1 items-center justify-center bg-bg px-6">
      <div className="w-full max-w-md">
        <h1 className="text-center font-serif text-[28px] text-text">
          Ask your documents anything.
        </h1>
        <div className="mt-6 flex flex-col gap-3">
          <Input autoFocus placeholder="Ask a question..." />
          <Button variant="primary" className="self-end">
            Ask
          </Button>
        </div>
      </div>
    </div>
  );
}
