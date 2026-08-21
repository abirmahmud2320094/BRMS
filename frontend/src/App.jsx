import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import AppShell from './components/AppShell'
import Loading from './components/Loading'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import BuildingPage from './pages/BuildingPage'
import FloorsPage from './pages/FloorsPage'
import ShopsPage from './pages/ShopsPage'
import TenantsPage from './pages/TenantsPage'
import RentPage from './pages/RentPage'
import UtilitiesPage from './pages/UtilitiesPage'
import MaintenancePage from './pages/MaintenancePage'
import ReportsPage from './pages/ReportsPage'
import UsersPage from './pages/UsersPage'
import NotFound from './pages/NotFound'
import { isAdministrator } from './utils/access'

function Protected(){const{user,loading}=useAuth();if(loading)return <div className="min-h-screen bg-slate-50"><Loading/></div>;return user?<AppShell/>:<Navigate to="/login" replace/>}
function AdminOnly({children}){const{user}=useAuth();return isAdministrator(user)?children:<Navigate to="/" replace/>}
export default function App(){return <Routes><Route path="/login" element={<LoginPage/>}/><Route element={<Protected/>}><Route index element={<DashboardPage/>}/><Route path="building" element={<BuildingPage/>}/><Route path="floors" element={<FloorsPage/>}/><Route path="shops" element={<ShopsPage/>}/><Route path="tenants" element={<TenantsPage/>}/><Route path="rent" element={<RentPage/>}/><Route path="utilities" element={<UtilitiesPage/>}/><Route path="maintenance" element={<MaintenancePage/>}/><Route path="reports" element={<ReportsPage/>}/><Route path="users" element={<AdminOnly><UsersPage/></AdminOnly>}/><Route path="*" element={<NotFound/>}/></Route></Routes>}
