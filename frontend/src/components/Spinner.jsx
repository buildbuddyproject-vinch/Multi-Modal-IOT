export default function Spinner({ size = "1.75rem" }) {
  return (
    <div className="d-flex justify-content-center align-items-center" style={{ padding: "1.5rem" }}>
      <div
        style={{
          width: size,
          height: size,
          border: "3px solid rgba(56, 189, 248, 0.25)",
          borderTopColor: "#38bdf8",
          borderRadius: "50%",
          animation: "icu-spin 0.7s linear infinite",
        }}
      />
      <style>{"@keyframes icu-spin { to { transform: rotate(360deg); } }"}</style>
    </div>
  );
}
