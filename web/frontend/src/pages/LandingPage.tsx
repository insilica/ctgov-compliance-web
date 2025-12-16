import {
  Banner,
  Card,
  CardBody,
  CardGroup,
  CardHeader,
  Grid,
  GridContainer,
  Icon,
  IconList,
  IconListContent,
  IconListIcon,
  IconListItem,
} from '@trussworks/react-uswds';
import { FormLayout } from '../components/FormLayout';
import { PrimaryButton } from '../components/PrimaryButton';
import { SignInPanel } from '../components/SignInPanel';

const checklistItems = [
  {
    icon: Icon.Security,
    title: 'Authentication parity',
    description: 'React routes hydrate from the same cookies and access policies as today.',
  },
  {
    icon: Icon.Assessment,
    title: 'Incremental delivery',
    description: 'Legacy Flask templates remain available while the React client rolls out.',
  },
  {
    icon: Icon.Insights,
    title: 'Storybook coverage',
    description: 'Components are documented and themed with USWDS for rapid discovery.',
  },
];

const featureCards = [
  {
    title: 'Real-time compliance snapshots',
    description:
      'Use the USWDS-based dashboard to review enrollment goals, audit tasks, and eligibility at a glance.',
  },
  {
    title: 'Shared component library',
    description:
      'Build future workflows faster with a single React component kit published through Storybook.',
  },
  {
    title: 'Secure rollouts',
    description:
      'Each page honors the existing auth middleware, keeping redirect logic and cookies untouched.',
  },
];

const quickActions = [
  {
    title: 'Review contracts',
    copy: 'Compare form fields across the old and new UI before flipping feature flags.',
  },
  {
    title: 'Validate authentications',
    copy: 'Confirm the auth provider refreshes tokens and guards protected routes.',
  },
];

export type LandingPageProps = {
  isAuthenticated: boolean;
  onSignOut?: () => void;
};

export function LandingPage({ isAuthenticated, onSignOut }: LandingPageProps) {
  const checklist = (
    <IconList>
      {checklistItems.map((item) => {
        const IconComponent = item.icon;
        return (
          <IconListItem key={item.title}>
            <IconListIcon>
              <IconComponent className="text-primary" aria-hidden="true" />
            </IconListIcon>
            <IconListContent title={item.title}>{item.description}</IconListContent>
          </IconListItem>
        );
      })}
    </IconList>
  );

  return (
    <div className="landing-page">
      <Banner />
      <main>
        <section className="usa-section usa-section--accent-cool">
          <GridContainer>
            <Grid row gap="lg" className="flex-align-center">
              <Grid mobileLg={{ col: 12 }} tablet={{ col: 7 }}>
                <p className="usa-intro text-primary">ClinicalTrials.gov Compliance workspace</p>
                <h1>Modernized workflows with react-uswds + Storybook.</h1>
                <p className="usa-prose">
                  Migrate page-by-page without touching backend auth. The React app consumes the same
                  cookies, headers, and redirect rules the Flask UI trusts today.
                </p>
                {isAuthenticated ? (
                  <div className="display-flex flex-wrap gap-2 margin-top-2">
                    <PrimaryButton onClick={onSignOut}>Sign out</PrimaryButton>
                    <PrimaryButton
                      className="usa-button--outline"
                      onClick={() => window.location.assign('/dashboard')}
                    >
                      Continue in React
                    </PrimaryButton>
                  </div>
                ) : (
                  <div className="margin-top-2">
                    <SignInPanel />
                  </div>
                )}
              </Grid>
              <Grid mobileLg={{ col: 12 }} tablet={{ col: 5 }}>
                {checklist}
              </Grid>
            </Grid>
          </GridContainer>
        </section>

        <section className="usa-section">
          <GridContainer>
            <CardGroup>
              {featureCards.map((card) => (
                <Card key={card.title} gridLayout={{ tablet: { col: 4 } }}>
                  <CardHeader>{card.title}</CardHeader>
                  <CardBody>{card.description}</CardBody>
                </Card>
              ))}
            </CardGroup>
          </GridContainer>
        </section>

        <section className="usa-section bg-base-lightest">
          <GridContainer>
            <FormLayout
              title="Quick compliance actions"
              description="Use these steps while migrating features into the React/Vite stack."
              actions={<PrimaryButton>View migration guide</PrimaryButton>}
            >
              <Grid row gap="md">
                {quickActions.map((action) => (
                  <Grid key={action.title} tablet={{ col: 6 }}>
                    <div className="usa-summary-box">
                      <div className="usa-summary-box__body">
                        <h4 className="usa-summary-box__heading">{action.title}</h4>
                        <p className="usa-summary-box__text">{action.copy}</p>
                      </div>
                    </div>
                  </Grid>
                ))}
              </Grid>
            </FormLayout>
          </GridContainer>
        </section>
      </main>
    </div>
  );
}
