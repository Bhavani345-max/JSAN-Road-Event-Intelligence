export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  /** A temporary password set by an administrator: a new one is chosen before anything else (decision 0044). */
  must_change_password?: boolean;
}
