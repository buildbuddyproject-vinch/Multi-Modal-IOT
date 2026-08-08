// Bootstrap ".alert" styling (from theme.css) applied to a plain div --
// equivalent to dash_bootstrap_components.Alert.
const COLOR_CLASS = {
  danger: "alert-danger",
  warning: "alert-warning",
  info: "alert-info",
  success: "alert-success",
};

export default function AlertBanner({ color = "info", children, className = "" }) {
  return <div className={`alert ${COLOR_CLASS[color] || "alert-info"} ${className}`}>{children}</div>;
}
