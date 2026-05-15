import React, { useState } from 'react';

interface TranslationBubbleProps {
  originalText: string;
  translatedText: string;
}

export function TranslationBubble({ originalText, translatedText }: TranslationBubbleProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <span 
      className="relative inline-block cursor-pointer group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <span className="underline decoration-dashed decoration-gray-400 decoration-1 underline-offset-4 hover:decoration-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
        {originalText}
      </span>
      
      {isHovered && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs z-10">
          <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 shadow-xl flex items-center gap-2">
            <span className="font-medium text-blue-300">Translation:</span>
            <span>{translatedText}</span>
          </div>
          {/* Tooltip arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </span>
  );
}
