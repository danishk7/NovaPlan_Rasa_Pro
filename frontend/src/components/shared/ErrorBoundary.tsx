import { type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

export default function ErrorBoundary({ children }: Props) {
  return <>{children}</>;
}