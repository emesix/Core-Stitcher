import { createRouter, createRoute, createRootRoute } from '@tanstack/react-router'
import { Layout } from './components/layout/Layout'
import { DeviceList, DeviceDetail, RunList, RunDetail, ReviewDetail } from './components/views'

const rootRoute = createRootRoute({
  component: Layout,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => (
    <div>
      <h1 style={{ color: 'var(--accent)', fontSize: '1.3rem' }}>Stitch WebUI</h1>
      <p style={{ color: 'var(--text-dim)', marginTop: 8 }}>
        Operator console ready. Select a resource from the sidebar.
      </p>
    </div>
  ),
})

const devicesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/devices',
  component: DeviceList,
})

const deviceDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/devices/$deviceId',
  component: () => {
    const { deviceId } = deviceDetailRoute.useParams()
    return <DeviceDetail deviceId={deviceId} />
  },
})

const runsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs',
  component: RunList,
})

const runDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runId',
  component: () => {
    const { runId } = runDetailRoute.useParams()
    return <RunDetail runId={runId} />
  },
})

const reviewDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/reviews/$reviewId',
  component: () => {
    const { reviewId } = reviewDetailRoute.useParams()
    return <ReviewDetail reviewId={reviewId} />
  },
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  devicesRoute,
  deviceDetailRoute,
  runsRoute,
  runDetailRoute,
  reviewDetailRoute,
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
