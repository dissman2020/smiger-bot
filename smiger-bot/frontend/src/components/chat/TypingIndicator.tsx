"use client";

export default function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in-up">
      <div className="w-8 h-8 rounded-full bg-brand-500 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1 shrink-0">
        S
      </div>
      <div className="bg-dark-800 border border-white/5 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
        <span className="w-2 h-2 bg-brand-400 rounded-full typing-dot" />
        <span className="w-2 h-2 bg-brand-400 rounded-full typing-dot" />
        <span className="w-2 h-2 bg-brand-400 rounded-full typing-dot" />
      </div>
    </div>
  );
}
