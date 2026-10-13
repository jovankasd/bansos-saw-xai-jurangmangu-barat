export type UserRole = "SUPER_ADMIN" | "VIEWER" | "SURVEYOR";

export interface User {
  id?: number;
  username?: string;
  name: string;
  role: UserRole;
  rt_number?: string | null;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, refreshToken: string, user: User) => void;
  logout: () => void;
}
