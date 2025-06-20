import Image from 'next/image';

interface LogoProps {
  size?: number;
  className?: string;
}

export function Logo({ size = 24, className = '' }: LogoProps) {
  return (
    <div className={`relative ${className}`}>
      <Image 
        src="/wolfstitch-logo.svg" 
        alt="Wolfstitch" 
        width={size} 
        height={size}
        className="brightness-0 invert"
        priority
      />
    </div>
  );
}