import { useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { AttentionDashboard } from "./components/AttentionDashboard";
import { CatchmentRequestPanel } from "./components/CatchmentRequestPanel";
import { ExecutiveWorkspace } from "./components/ExecutiveWorkspace";
import { M1Workspace } from "./components/M1Workspace";
import { ManagerAssignments } from "./components/ManagerAssignments";
import { ManagerCatchmentDetail } from "./components/ManagerCatchmentDetail";
import { ManagerPipeline } from "./components/ManagerPipeline";
import { SavedReportDetail, SavedReports } from "./components/SavedReports";
import { SubmittedProperties } from "./components/SubmittedProperties";
import { RoleShell, roleHome, type RoleId } from "./components/RoleShell";
import { SurveyExecutiveWorkspace } from "./components/SurveyExecutiveWorkspace";
import { SurveyManagerWorkspace } from "./components/SurveyManagerWorkspace";
import { setDemoIdentity } from "./services/api";
import { getHealth, type HealthResponse } from "./services/health";

const rolePrefixes: Array<[string, RoleId]> = [
  ["/survey-executive", "survey-executive"],
  ["/survey-manager", "survey-manager"],
  ["/executive", "bd-executive"],
  ["/manager", "bd-manager"]
];

function roleFromPath(pathname: string): RoleId {
  return rolePrefixes.find(([prefix]) => pathname.startsWith(prefix))?.[1] ?? "bd-manager";
}

export function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeRole = roleFromPath(location.pathname);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [identityVersion, setIdentityVersion] = useState(0);

  useEffect(() => {
    function refreshHealth() {
      getHealth().then((result) => {
        setHealth(result);
        setHealthError(null);
      }).catch((error: unknown) => {
        setHealthError(error instanceof Error ? error.message : "Unable to reach API");
      });
    }
    refreshHealth();
    const timer = window.setInterval(refreshHealth, 15_000);
    return () => window.clearInterval(timer);
  }, []);

  const currentUserId = useMemo(() => {
    const storedRole = window.localStorage.getItem("sitescout-role");
    const storedUser = window.localStorage.getItem("sitescout-user-id");
    const fallback = activeRole === "bd-manager" ? "bd-manager-1" : activeRole === "bd-executive" ? "bd-executive-1" : activeRole === "survey-manager" ? "survey-manager-1" : "survey-executive-1";
    return storedRole === activeRole && storedUser ? storedUser : fallback;
  }, [activeRole, identityVersion]);

  useEffect(() => {
    setDemoIdentity({ role: activeRole, userId: currentUserId });
  }, [activeRole, currentUserId]);

  function changeRole(role: RoleId) {
    const userId = role === "bd-manager" ? "bd-manager-1" : role === "bd-executive" ? "bd-executive-1" : role === "survey-manager" ? "survey-manager-1" : "survey-executive-1";
    setDemoIdentity({ role, userId });
    setIdentityVersion((value) => value + 1);
    navigate(roleHome[role]);
  }

  function changeUser(userId: string) {
    setDemoIdentity({ role: activeRole, userId });
    setIdentityVersion((value) => value + 1);
  }

  return (
    <RoleShell activeRole={activeRole} currentUserId={currentUserId} health={health} healthError={healthError} onRoleChange={changeRole} onUserChange={changeUser}>
      <div className="route-stage" key={`${location.pathname}:${currentUserId}`}>
        <Routes>
          <Route path="/manager" element={<AttentionDashboard role="bd-manager" />} />
          <Route path="/manager/areas" element={<M1Workspace />} />
          <Route path="/manager/reports" element={<SavedReports />} />
          <Route path="/manager/reports/:reportId" element={<SavedReportDetail />} />
          <Route path="/manager/assignments" element={<ManagerAssignments />} />
          <Route path="/manager/properties" element={<ManagerPipeline />} />
          <Route path="/manager/properties/:propertyId" element={<ManagerPipeline />} />
          <Route path="/manager/catchments" element={<CatchmentRequestPanel />} />
          <Route path="/manager/catchments/:studyId" element={<ManagerCatchmentDetail />} />
          <Route path="/manager/decisions" element={<ManagerPipeline view="decisions" />} />
          <Route path="/executive" element={<AttentionDashboard role="bd-executive" />} />
          <Route path="/executive/assignments" element={<ExecutiveWorkspace />} />
          <Route path="/executive/assignments/:assignmentId" element={<ExecutiveWorkspace />} />
          <Route path="/executive/submitted" element={<SubmittedProperties />} />
          <Route path="/executive/properties/:propertyId" element={<SubmittedProperties />} />
          <Route path="/survey-manager" element={<AttentionDashboard role="survey-manager" />} />
          <Route path="/survey-manager/requests" element={<SurveyManagerWorkspace view="requests" />} />
          <Route path="/survey-manager/progress" element={<SurveyManagerWorkspace view="progress" />} />
          <Route path="/survey-manager/results" element={<SurveyManagerWorkspace view="results" />} />
          <Route path="/survey-manager/studies/:studyId" element={<SurveyManagerWorkspace view="detail" />} />
          <Route path="/survey-executive" element={<AttentionDashboard role="survey-executive" />} />
          <Route path="/survey-executive/zones" element={<SurveyExecutiveWorkspace view="zones" />} />
          <Route path="/survey-executive/zones/:zoneId" element={<SurveyExecutiveWorkspace view="zones" />} />
          <Route path="/survey-executive/drafts" element={<SurveyExecutiveWorkspace view="drafts" />} />
          <Route path="/survey-manager/studies" element={<Navigate to="/survey-manager/requests" replace />} />
          <Route path="/" element={<Navigate to="/manager" replace />} />
          <Route path="*" element={<Navigate to={roleHome[activeRole]} replace />} />
        </Routes>
      </div>
    </RoleShell>
  );
}
